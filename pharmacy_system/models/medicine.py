from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_is_zero


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =========================================================================
    # FIELDS: COMMISSION
    # =========================================================================
    commission_percentage = fields.Float(
        string='Commission %',
        digits=(16, 2),
        help='Commission percentage used to calculate margin-based commission on sales order lines.',
    )

    commission_feature_enabled = fields.Boolean(
        string='Commission Feature Enabled',
        compute='_compute_commission_feature_enabled',
        default=lambda self: self.env.company.enable_product_commission,
    )

    # =========================================================================
    # FIELDS: PRICE / COST / HISTORY
    # =========================================================================
    price_history_ids = fields.One2many(
        'product.price.history',
        'product_id',
        string='Price History',
        groups="pharmacy_base.group_pharmacy_manager",
    )

    # =========================================================================
    # FIELDS: SALES LIMITS
    # =========================================================================
    max_qty_per_invoice = fields.Integer(
        string='Max package per Invoice',
        help='Hard limit on quantity per sale invoice — applies at all stock levels.',
    )

    # =========================================================================
    # FIELDS: LOW STOCK CONTROL
    # =========================================================================
    activate_stock_low = fields.Boolean(
        string='Enable Low Stock Control',
        help='If enabled, low stock rules will apply. Otherwise, fixed max per invoice is used.',
    )

    low_stock_limit = fields.Integer(
        string='Low Stock Limit',
    )

    max_qty_low_stock = fields.Integer(
        string='Max package per Invoice When Low',
    )

    is_low_stock = fields.Boolean(
        string='Is Low Stock',
        compute='_compute_is_low_stock',
        store=False,
    )

    low_stock_log_ids = fields.One2many(
        'low.stock.log',
        'product_tmpl_id',
        string='Low Stock Logs',
        groups="pharmacy_base.group_pharmacy_manager",
    )

    log_count = fields.Integer(
        string='Logs Count',
        compute='_compute_log_count',
        groups="pharmacy_base.group_pharmacy_manager",
    )

    # =========================================================================
    # COMPUTE METHODS: COMMISSION
    # =========================================================================
    @api.depends_context('company')
    def _compute_commission_feature_enabled(self):
        enabled = self.env.company.enable_product_commission
        for rec in self:
            rec.commission_feature_enabled = enabled

    # =========================================================================
    # COMPUTE METHODS: LOW STOCK
    # =========================================================================
    def _compute_log_count(self):
        is_manager = self.env.user.has_group('pharmacy_base.group_pharmacy_manager')
        for rec in self:
            if is_manager:
                rec.log_count = len(rec.low_stock_log_ids)
            else:
                rec.log_count = 0

    @api.depends('qty_available', 'low_stock_limit')
    def _compute_is_low_stock(self):
        for rec in self:
            rec.is_low_stock = bool(
                rec.low_stock_limit
                and rec.qty_available <= rec.low_stock_limit
            )

    # =========================================================================
    # CONSTRAINTS: COMMISSION
    # =========================================================================
    @api.constrains('commission_percentage')
    def _check_commission_percentage(self):
        for rec in self:
            if rec.commission_percentage < 0 or rec.commission_percentage > 100:
                raise ValidationError(_('Commission % must be between 0 and 100.'))

    # =========================================================================
    # CONSTRAINTS: SALES LIMITS
    # =========================================================================
    @api.constrains('max_qty_per_invoice')
    def _check_max_qty(self):
        for rec in self:
            if rec.max_qty_per_invoice < 0:
                raise ValidationError(_('Max Qty must be positive'))

    # =========================================================================
    # CONSTRAINTS: LOW STOCK CONTROL
    # =========================================================================
    @api.constrains('low_stock_limit', 'max_qty_low_stock')
    def _check_limits(self):
        for rec in self:
            if rec.low_stock_limit and rec.max_qty_low_stock:
                if rec.max_qty_low_stock >= rec.low_stock_limit:
                    raise ValidationError(_('Max Qty must be less than Low Stock Limit.'))

    @api.constrains(
        'activate_stock_low',
        'low_stock_limit',
        'max_qty_low_stock',
        'max_qty_per_invoice',
    )
    def _check_stock_configuration(self):
        for rec in self:
            if rec.activate_stock_low:
                if not rec.low_stock_limit or not rec.max_qty_low_stock:
                    raise ValidationError(_(
                        'When Low Stock Control is enabled, you must set:\n'
                        '- Low Stock Limit\n'
                        '- Max package When Low Stock'
                    ))

                if rec.max_qty_per_invoice:
                    raise ValidationError(_(
                        'Max package Per Invoice must be 0 when Low Stock Control is enabled.'
                    ))
            else:
                if not rec.max_qty_per_invoice:
                    raise ValidationError(_(
                        'You must set Max package Per Invoice when Low Stock Control is disabled.'
                    ))

                if rec.low_stock_limit or rec.max_qty_low_stock:
                    raise ValidationError(_(
                        'Low stock fields must be empty when Low Stock Control is disabled.'
                    ))

    # =========================================================================
    # ONCHANGE METHODS: LOW STOCK CONTROL
    # =========================================================================
    @api.onchange('activate_stock_low')
    def _onchange_activate_stock_low(self):
        for rec in self:
            if rec.activate_stock_low:
                rec.max_qty_per_invoice = 0
            else:
                rec.low_stock_limit = 0
                rec.max_qty_low_stock = 0

    # =========================================================================
    # HELPERS: WRITE VALIDATIONS
    # =========================================================================
    def _check_tracking_change_allowed(self, vals):
        if 'tracking' not in vals:
            return

        for rec in self:
            has_stock_moves = self.env['stock.move'].search_count([
                ('product_id', 'in', rec.product_variant_ids.ids),
                ('state', '!=', 'cancel'),
            ], limit=1)

            if has_stock_moves and rec.tracking != vals['tracking']:
                tracking_selection = dict(rec._fields['tracking'].selection)
                current_label = tracking_selection.get(rec.tracking, rec.tracking)
                new_label = tracking_selection.get(vals['tracking'], vals['tracking'])

                raise UserError(_(
                    'Cannot change tracking method for product "%(name)s" '
                    'because it already has stock transactions.\n'
                    'Current tracking: %(current)s\n'
                    'Attempted change to: %(new)s'
                ) % {
                    'name': rec.name,
                    'current': current_label,
                    'new': new_label,
                })

    def _prepare_old_public_prices(self, vals):
        if 'public_price' not in vals:
            return {}
        return {rec.id: getattr(rec, 'public_price', 0.0) for rec in self}

    def _create_public_price_history(self, old_prices, vals):
        if 'public_price' not in vals:
            return

        for rec in self:
            old_price = old_prices.get(rec.id)
            if old_price is not None and vals['public_price'] != old_price:
                self.env['product.price.history'].create({
                    'product_id': rec.id,
                    'old_price': old_price,
                    'new_price': rec.public_price,
                    'changed_by': self.env.user.id,
                })

                rec.message_post(
                    body=_('Price changed: %(old)s → %(new)s') % {
                        'old': old_price,
                        'new': rec.public_price,
                    }
                )

    # =========================================================================
    # ORM OVERRIDES: CREATE / WRITE
    # =========================================================================
    def write(self, vals):
        vals = dict(vals)
        self._check_tracking_change_allowed(vals)

        old_prices = self._prepare_old_public_prices(vals)
        res = super().write(vals)
        self._create_public_price_history(old_prices, vals)
        return res

    def action_open_expired_stock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Stock',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id.product_tmpl_id', '=', self.id),
                ('location_id.is_expired_location', '=', True)
            ],
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # =========================================================================
    # POS DATA
    # =========================================================================
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)

        extra_fields = [
            'x_is_scheduled',
            'x_schedule_level',
            'x_pos_similar_product_ids',
            'x_pos_complementary_product_ids',
            'x_has_pos_related_products',
            'qty_expired',
            'qty_available',
        ]

        for field in extra_fields:
            if field not in fields_list:
                fields_list.append(field)

        return fields_list

    def _pos_domain(self):
        """Allow out-of-stock products to load so they can be added to the Wishlist."""
        return super()._pos_domain() if hasattr(super(), "_pos_domain") else []

    def _get_non_expired_qty(self):
        self.env.cr.execute("""
            SELECT product_id, SUM(quantity) as qty
            FROM stock_quant q
            JOIN stock_location l ON l.id = q.location_id
            WHERE l.is_expired_location = FALSE
            GROUP BY product_id
        """)
        return dict(self.env.cr.fetchall())

    def action_open_expired_stock_variant(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Stock',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id', '=', self.id),
                ('location_id.is_expired_location', '=', True)
            ],
            'context': {
                'search_default_expired_stock': 1,
            }
        }

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super()._compute_quantities_dict(
            lot_id, owner_id, package_id, from_date, to_date
        )

        for product in self:
            # remove expired stock from results
            # We use sudo() here because is_expired_location is group-restricted
            expired_quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id.is_expired_location', '=', True)
            ])

            expired_qty = sum(expired_quants.mapped('quantity'))

            res[product.id]['qty_available'] -= expired_qty
            res[product.id]['virtual_available'] -= expired_qty

        return res
