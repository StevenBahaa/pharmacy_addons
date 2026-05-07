from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_is_zero


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =========================================================================
    # FIELDS: PACKAGE / UNIT
    # =========================================================================
    sell_as = fields.Selection(
        [
            ('package', 'Package'),
            ('unit', 'Unit'),
        ],
        string='Sell As',
        default='package',
        required=True,
    )

    units_per_package = fields.Integer(
        string='Units per Package',
    )

    package_uom_id = fields.Many2one(
        'uom.uom',
        string='Package UoM',
        readonly=True,
    )

    # =========================================================================
    # FIELDS: CLASSIFICATION / MEDICINE INFO
    # =========================================================================
    x_classification = fields.Selection(
        [
            ('medicine', 'Medicine'),
            ('non_medicine', 'Non-Medicine'),
        ],
        string='Classification',
        required=True,
        tracking=True,
        help='Specify whether the product is a medicine or not.',
    )

    generic_name = fields.Char(
        string='Generic / Scientific Name',
        help='Scientific / INN name of the product.',
    )

    manufacturer_id = fields.Many2one(
        'res.partner',
        string='Manufacturer',
        domain="[('is_manufacturer', '=', True)]",
        help='Manufacturer linked from contacts.',
    )

    # =========================================================================
    # FIELDS: SCHEDULED MEDICINE
    # =========================================================================
    x_is_scheduled = fields.Boolean(
        string='Scheduled Medicine',
    )

    x_schedule_level = fields.Selection(
        [
            ('schedule_1', 'Schedule I'),
            ('schedule_2', 'Schedule II'),
            ('schedule_3', 'Schedule III'),
            ('schedule_4', 'Schedule IV'),
            ('schedule_5', 'Schedule V'),
        ],
        string='Schedule Level',
        tracking=True,
    )

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
    public_price = fields.Float(
        string='Public Price',
        required=True,
        tracking=True,
    )

    gov_price_lock = fields.Boolean(
        string='Government Price Lock',
        default=False,
    )

    price_history_ids = fields.One2many(
        'product.price.history',
        'product_id',
        string='Price History',
    )

    currency_display_price = fields.Monetary(
        string='Price (Other Currency)',
        compute='_compute_currency_display_price',
        currency_field='currency_id',
    )

    x_avg_cost_display = fields.Char(
        string='Avg. Purchase Cost',
        compute='_compute_x_avg_cost_display',
        store=False,
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
    )

    log_count = fields.Integer(
        string='Logs Count',
        compute='_compute_log_count',
    )

    # =========================================================================
    # FIELDS: RELATED PRODUCT
    # =========================================================================

    similar_product_ids  = fields.One2many(
        comodel_name='product.related.product',
        inverse_name='product_id',
        string='Similar / Alternative Products',
        domain=[('relation_type' , '=' , 'similar')]
    )

    complementary_product_ids   = fields.One2many(
        comodel_name='product.related.product',
        inverse_name='product_id',
        string='Complementary  Products',
        domain=[('relation_type' , '=' , 'complementary')]
    )

        # SC1-UC-01: Field to store the last discount from vendor bills
    x_last_purchase_discount = fields.Float(
        string="Last Purchase Discount (%)",
        help="This field is automatically updated from the last validated vendor bill.",
        readonly=True
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
    # COMPUTE METHODS: PRICE / COST
    # =========================================================================
    @api.depends(
        'standard_price',
        'product_variant_ids.standard_price',
        'sell_as',
        'uom_id',
        'package_uom_id',
    )
    @api.depends_context('company')
    def _compute_x_avg_cost_display(self):
        for rec in self:
            # Prefer variant cost because product.template standard_price
            # can be empty/indirect in some flows.
            product = rec.product_variant_id or rec.product_variant_ids[:1]
            cost_in_package = product.standard_price if product else (rec.standard_price or 0.0)

            effective_cost = cost_in_package

            precision_rounding = rec.currency_id.rounding if rec.currency_id else 0.01
            if not float_is_zero(effective_cost, precision_rounding=precision_rounding):
                rec.x_avg_cost_display = f'{effective_cost:.3f}'
            else:
                rec.x_avg_cost_display = '--'

    @api.depends('public_price')
    def _compute_currency_display_price(self):
        for rec in self:
            company = rec.env.company
            target_currency = (
                rec.env.context.get('currency_id')
                and rec.env['res.currency'].browse(rec.env.context['currency_id'])
                or company.currency_id
            )

            rec.currency_display_price = company.currency_id._convert(
                rec.public_price,
                target_currency,
                company,
                fields.Date.today(),
            )

    # =========================================================================
    # COMPUTE METHODS: LOW STOCK
    # =========================================================================
    def _compute_log_count(self):
        for rec in self:
            rec.log_count = len(rec.low_stock_log_ids)

    @api.depends('qty_available', 'low_stock_limit')
    def _compute_is_low_stock(self):
        for rec in self:
            rec.is_low_stock = bool(
                rec.low_stock_limit
                and rec.qty_available <= rec.low_stock_limit
            )

    # =========================================================================
    # CONSTRAINTS: PACKAGE / UNIT
    # =========================================================================
    @api.constrains('sell_as', 'units_per_package')
    def _check_units(self):
        for rec in self:
            if rec.sell_as == 'unit' and rec.units_per_package <= 0:
                raise ValidationError(_('Units per package must be > 0'))

    # =========================================================================
    # CONSTRAINTS: COMMISSION
    # =========================================================================
    @api.constrains('commission_percentage')
    def _check_commission_percentage(self):
        for rec in self:
            if rec.commission_percentage < 0 or rec.commission_percentage > 100:
                raise ValidationError(_('Commission % must be between 0 and 100.'))

    # =========================================================================
    # CONSTRAINTS: PRICE
    # =========================================================================
    @api.constrains('public_price')
    def _check_price_positive(self):
        for rec in self:
            if rec.public_price <= 0:
                raise ValidationError(_('Public price must be greater than 0'))

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
    # ONCHANGE METHODS: CLASSIFICATION
    # =========================================================================
    @api.onchange('x_classification')
    def _onchange_x_classification(self):
        if not self.id:
            if self.x_classification == 'medicine':
                self.tracking = 'lot'
            elif self.x_classification == 'non_medicine':
                self.tracking = 'none'

    # =========================================================================
    # ONCHANGE METHODS: PACKAGE / UNIT
    # =========================================================================
    @api.onchange('sell_as', 'units_per_package')
    def _onchange_sell_as(self):
        for rec in self:
            if rec.sell_as == 'unit' and rec.units_per_package and rec.units_per_package > 0:
                package_uom = rec._get_or_create_package_uom()
                rec.uom_id = package_uom
                rec.uom_po_id = package_uom
                rec.package_uom_id = rec._create_or_get_unit_ratio_uom()
            else:
                rec.package_uom_id = False

    @api.onchange('type')
    def _onchange_force_package_uom(self):
        for rec in self:
            if not rec.id:
                package_uom = rec._get_or_create_package_uom()
                rec.uom_id = package_uom
                rec.uom_po_id = package_uom

    # =========================================================================
    # ONCHANGE METHODS: PRICE
    # =========================================================================
    @api.onchange('public_price')
    def _onchange_public_price(self):
        self.list_price = self.public_price

        if self.standard_price and self.public_price < self.standard_price:
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Selling below cost. Confirm?'),
                }
            }

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
    # ONCHANGE METHODS: WARNINGS / UX
    # =========================================================================
    @api.onchange('name')
    def _onchange_name_duplicate_warning(self):
        for rec in self:
            if not rec.name:
                continue

            domain = [('name', '=ilike', rec.name.strip())]
            if rec.id:
                domain.append(('id', '!=', rec.id))

            duplicate = self.search(domain, limit=1)
            if duplicate:
                return {
                    'warning': {
                        'title': _('Duplicate Product Name'),
                        'message': _(
                            'Another product with the name "%s" already exists.\n'
                            'Please check whether this is intentional.'
                        ) % rec.name,
                    }
                }

    @api.onchange('categ_id')
    def _onchange_categ_id_warning(self):
        if not self.categ_id:
            return {
                'warning': {
                    'title': _('Category Required'),
                    'message': _('Please select a category for this product.'),
                }
            }

    # =========================================================================
    # HELPERS: PACKAGE / UNIT
    # =========================================================================
    def _get_or_create_package_uom(self):
        category = self.env['uom.category'].sudo().search([
            ('name', '=', 'Package'),
        ], limit=1)

        if not category:
            category = self.env['uom.category'].sudo().create({
                'name': 'Package',
            })

        package_uom = self.env['uom.uom'].sudo().search([
            ('name', '=', 'Package'),
            ('category_id', '=', category.id),
        ], limit=1)

        if not package_uom:
            package_uom = self.env['uom.uom'].sudo().create({
                'name': 'Package',
                'category_id': category.id,
                'uom_type': 'reference',
                'factor': 1.0,
                'rounding': 0.01,
            })

        return package_uom

    def _create_or_get_unit_ratio_uom(self):
        self.ensure_one()

        if not self.units_per_package or self.units_per_package <= 0:
            raise ValidationError(_('Units per package must be greater than zero.'))

        package_uom = self._get_or_create_package_uom()
        name = f'1 unit of {int(self.units_per_package)} units per Package'

        uom = self.env['uom.uom'].sudo().search([
            ('name', '=', name),
            ('category_id', '=', package_uom.category_id.id),
        ], limit=1)

        if not uom:
            uom = self.env['uom.uom'].sudo().create({
                'name': name,
                'category_id': package_uom.category_id.id,
                'uom_type': 'smaller',
                # 1 package = N units, so 1 unit = 1/N package.
                'factor': self.units_per_package,
                'rounding': 0.01,
            })

        return uom

    # =========================================================================
    # HELPERS: WRITE VALIDATIONS
    # =========================================================================
    def _check_gov_price_lock_access(self, vals):
        if 'gov_price_lock' not in vals:
            return

        for rec in self:
            if vals['gov_price_lock'] and not rec.gov_price_lock:
                if not self.env.user.has_group('pharmacy_system.group_pharmacy_manager'):
                    raise ValidationError(_(
                        'Only a Pharmacy Manager can enable Government Price Lock.'
                    ))

            if not vals['gov_price_lock'] and rec.gov_price_lock:
                if not self.env.user.has_group('pharmacy_system.group_pharmacy_manager'):
                    raise ValidationError(_(
                        'Only a Pharmacy Manager can disable Government Price Lock.'
                    ))

    def _check_public_price_change_allowed(self, vals):
        if 'public_price' not in vals:
            return

        for rec in self:
            if rec.gov_price_lock:
                raise UserError(_('Price is government-regulated and cannot be changed.'))

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
        return {rec.id: rec.public_price for rec in self}

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

    def _sync_package_uom_after_write(self):
        for rec in self:
            if rec.sell_as == 'unit' and rec.units_per_package:
                uom = rec._create_or_get_unit_ratio_uom()

                # Safe assignment: avoids recursive write loop.
                if rec.package_uom_id != uom:
                    super(ProductTemplate, rec).write({
                        'package_uom_id': uom.id,
                    })

    # =========================================================================
    # ORM OVERRIDES: CREATE / WRITE
    # =========================================================================
    @api.model_create_multi
    def create(self, vals_list):
        package_uom = self._get_or_create_package_uom()

        for vals in vals_list:
            # Business rule: native product UoM is always Package.
            vals['uom_id'] = package_uom.id
            vals['uom_po_id'] = package_uom.id

            if vals.get('gov_price_lock'):
                if not self.env.user.has_group('pharmacy_system.group_pharmacy_manager'):
                    raise ValidationError(_(
                        'Only a Pharmacy Manager can enable Government Price Lock.'
                    ))

        records = super().create(vals_list)

        for rec in records:
            if rec.sell_as == 'unit' and rec.units_per_package:
                uom = rec._create_or_get_unit_ratio_uom()
                super(ProductTemplate, rec).write({
                    'package_uom_id': uom.id,
                })

        return records

    def write(self, vals):
        vals = dict(vals)

        self._check_gov_price_lock_access(vals)
        self._check_public_price_change_allowed(vals)
        self._check_tracking_change_allowed(vals)

        old_prices = self._prepare_old_public_prices(vals)

        res = super().write(vals)

        self._create_public_price_history(old_prices, vals)
        self._sync_package_uom_after_write()

        return res

    # =========================================================================
    # SEARCH OVERRIDES
    # =========================================================================
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []

        if name:
            domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('generic_name', operator, name)],
            ])
            args = expression.AND([args, domain])

        return self._search(args, limit=limit)
    
    qty_expired = fields.Float(
        string="Expired Qty",
        compute="_compute_expired_qty"
    )

    def _compute_expired_qty(self):
        for template in self:
            template.qty_expired = sum(
                template.product_variant_ids.mapped('qty_expired')
            )

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
    # FIELDS: SCHEDULED MEDICINE FOR POS
    # =========================================================================
    x_is_scheduled = fields.Boolean(
        related='product_tmpl_id.x_is_scheduled',
        store=True,
        readonly=True,
    )

    x_schedule_level = fields.Selection(
        related='product_tmpl_id.x_schedule_level',
        store=True,
        readonly=True,
    )

    # =========================================================================
    # FIELDS: RELATED MEDICINE FOR POS
    # ==================================== =====================================

    x_pos_similar_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='POS Similar Products',
        compute='_compute_pos_related_products',
    )

    x_pos_complementary_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='POS Complementary Products',
        compute='_compute_pos_related_products',
    )

    x_has_pos_related_products = fields.Boolean(
        string='Has POS Related Products',
        compute='_compute_pos_related_products',
    )

    # =========================================================================
    # ORM OVERRIDES: CREATE INTERNAL REFERENCE
    # =========================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                vals['default_code'] = self.env['ir.sequence'].next_by_code(
                    'product.internal.reference'
                ) or '/'

        return super().create(vals_list)

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

    # =========================================================================
    # SEARCH OVERRIDES
    # =========================================================================
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []

        if name:
            domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('product_tmpl_id.generic_name', operator, name)],
            ])
            args = expression.AND([args, domain])

        return self._search(args, limit=limit)
    
    @api.depends(
        'product_tmpl_id.similar_product_ids',
        'product_tmpl_id.complementary_product_ids',
        'product_tmpl_id.similar_product_ids.related_product_id',
        'product_tmpl_id.complementary_product_ids.related_product_id',
        'product_tmpl_id.similar_product_ids.active',
        'product_tmpl_id.complementary_product_ids.active',
        'product_tmpl_id.similar_product_ids.priority',
        'product_tmpl_id.complementary_product_ids.priority',
    )
    def _compute_pos_related_products(self):
        for product in self:
            similar_lines = product.product_tmpl_id.similar_product_ids.filtered(
                lambda line: line.active and line.related_product_id
            ).sorted(lambda line: line.priority, reverse=True)

            complementary_lines = product.product_tmpl_id.complementary_product_ids.filtered(
                lambda line: line.active and line.related_product_id
            ).sorted(lambda line: line.priority, reverse=True)

            similar_products = similar_lines.mapped('related_product_id.product_variant_id')
            complementary_products = complementary_lines.mapped('related_product_id.product_variant_id')

            product.x_pos_similar_product_ids = similar_products
            product.x_pos_complementary_product_ids = complementary_products
            product.x_has_pos_related_products = bool(similar_products or complementary_products)

    qty_expired = fields.Float(
        string="Expired Qty",
        compute="_compute_expired_qty"
    )

    def _compute_expired_qty(self):
        for product in self:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.is_expired_location', '=', True)
            ])
            product.qty_expired = sum(quants.mapped('quantity'))
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
    def _load_pos_data(self, data):
        return super()._load_pos_data(data)
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
            expired_quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.is_expired_location', '=', True)
            ])

            expired_qty = sum(expired_quants.mapped('quantity'))

            res[product.id]['qty_available'] -= expired_qty
            res[product.id]['virtual_available'] -= expired_qty

        return res


    
