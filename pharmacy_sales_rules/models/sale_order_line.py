from collections import defaultdict

from odoo import _, api, fields, models
from datetime import date
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # -------------------------------------------------------------------------
    # FIELDS: RELATED / REPORTING
    # -------------------------------------------------------------------------
    salesman_id = fields.Many2one(
        related='order_id.user_id',
        string='Salesperson',
        store=True,
        readonly=True,
    )

    order_date = fields.Datetime(
        related='order_id.date_order',
        string='Order Date',
        store=True,
        readonly=True,
    )

    low_stock_override = fields.Boolean(default=False)
    stock_at_sale = fields.Float()


    # -------------------------------------------------------------------------
    # FIELDS: ALLOWED UOM
    # -------------------------------------------------------------------------
    allowed_sale_uom_ids = fields.Many2many(
        'uom.uom',
        compute='_compute_allowed_sale_uom_ids',
        string='Allowed Sale UoMs',
    )

    x_package_uom_id = fields.Many2one(
        'uom.uom',
        compute='_compute_sale_uom_refs',
        string='Package UoM',
    )

    x_ratio_uom_id = fields.Many2one(
        'uom.uom',
        compute='_compute_sale_uom_refs',
        string='Ratio UoM',
    )

    x_sale_uom_readonly = fields.Boolean(
        compute='_compute_sale_uom_refs',
        string='Sale UoM Readonly',
    )

    # -------------------------------------------------------------------------
    # FIELDS: COMMISSION
    # -------------------------------------------------------------------------
    commission_percentage = fields.Float(
        string='Commission %',
        digits=(16, 2),
        readonly=True,
        copy=False,
    )

    commission_cost_snapshot = fields.Float(
        string='Cost Snapshot',
        digits='Product Price',
        readonly=True,
        copy=False,
        help='Native Odoo average cost captured in the selected sale UoM.',
    )

    commission_margin_base = fields.Monetary(
        string='Commission Margin Base',
        currency_field='currency_id',
        compute='_compute_commission_fields',
        store=True,
        readonly=True,
    )

    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_commission_fields',
        store=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # FIELDS: RELATED PRODUCT
    # -------------------------------------------------------------------------

    similar_related_product_ids = fields.Many2many(
        comodel_name='product.template',
        string='Similar / Alternative Products',
        compute='_compute_related_product_suggestions',
    )

    complementary_related_product_ids = fields.Many2many(
        comodel_name='product.template',
        string='Complementary Products',
        compute='_compute_related_product_suggestions',
    )

    # -------------------------------------------------------------------------
    # HELPERS: COMMISSION ELIGIBILITY
    # -------------------------------------------------------------------------
    def _is_commission_eligible_line(self):
        self.ensure_one()

        if not self.product_id or self.display_type or self.is_downpayment:
            return False
        if (self.discount or 0.0) > 0.0:
            return False
        if self.price_unit <= 0.0:
            return False
        if hasattr(self, 'is_reward_line') and self.is_reward_line:
            return False
        if self._order_has_discount_or_coupon_lines():
            return False
        return True

    def _order_has_discount_or_coupon_lines(self):
        """Return True when the order has any discount/coupon/reward-like line."""
        self.ensure_one()
        order = self.order_id
        if not order:
            return False

        for line in order.order_line.filtered(lambda l: not l.display_type):
            if not line.product_id:
                continue
            if (line.discount or 0.0) > 0.0:
                return True
            if hasattr(line, 'is_reward_line') and line.is_reward_line:
                return True
            # Reward/coupon lines are often negative priced.
            # Do not treat zero price as coupon during draft onchange.
            if (line.price_unit or 0.0) < 0.0:
                return True
            if line.is_downpayment:
                return True
        return False

    # -------------------------------------------------------------------------
    # COMPUTE: ALLOWED UOM
    # -------------------------------------------------------------------------
    @api.depends(
        'product_id',
        'product_template_id',
        'product_id.product_tmpl_id.package_uom_id',
        'product_template_id.package_uom_id',
        'product_id.uom_id',
        'product_template_id.uom_id',
    )
    def _compute_allowed_sale_uom_ids(self):
        for line in self:
            allowed_uoms = line._get_allowed_sale_uoms()
            line.allowed_sale_uom_ids = [(6, 0, allowed_uoms.ids)]


    @api.depends('product_id', 'product_template_id')
    def _compute_sale_uom_refs(self):
        for line in self:
            product = line.product_id
            tmpl = product.product_tmpl_id if product else line.product_template_id

            line.x_package_uom_id = False
            line.x_ratio_uom_id = False
            line.x_sale_uom_readonly = False

            if not tmpl:
                continue

            # Native product UoM = Package
            line.x_package_uom_id = tmpl.uom_id

            # Product-specific ratio UoM is only valid when sell_as = unit
            if tmpl.sell_as == 'unit':
                line.x_ratio_uom_id = tmpl.package_uom_id

            # For package-only products, lock sale UoM on package.
            line.x_sale_uom_readonly = (tmpl.sell_as == 'package')

    # -------------------------------------------------------------------------
    # COMPUTE: COMMISSION
    # -------------------------------------------------------------------------
    @api.depends(
        'product_id',
        'product_uom',
        'product_uom_qty',
        'price_unit',
        'discount',
        'commission_percentage',
        'commission_cost_snapshot',
        'order_id.company_id.enable_product_commission',
    )
    def _compute_commission_fields(self):
        for line in self:
            company = line.order_id.company_id or self.env.company

            if not company.enable_product_commission or not line._is_commission_eligible_line():
                line.commission_margin_base = 0.0
                line.commission_amount = 0.0
                continue

            unit_price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            unit_margin = max(
                unit_price - (line.commission_cost_snapshot or 0.0),
                0.0,
            )

            line.commission_margin_base = unit_margin * line.product_uom_qty
            line.commission_amount = (
                line.commission_margin_base
                * (line.commission_percentage or 0.0)
                / 100.0
            )

    # -------------------------------------------------------------------------
    # COMPUTE: RELATED PRODUCT
    # -------------------------------------------------------------------------

    @api.depends('product_id')
    def _compute_related_product_suggestions(self):
        RelatedProduct = self.env['product.related.product']

        for line in self:
            line.similar_related_product_ids = False
            line.complementary_related_product_ids = False

            if not line.product_id:
                continue

            product_tmpl = line.product_id.product_tmpl_id

            similar_relations = RelatedProduct.search([
                ('product_id', '=', product_tmpl.id),
                ('relation_type', '=', 'similar'),
                ('active', '=', True),
            ])

            complementary_relations = RelatedProduct.search([
                ('product_id', '=', product_tmpl.id),
                ('relation_type', '=', 'complementary'),
                ('active', '=', True),
            ])

            line.similar_related_product_ids = similar_relations.mapped('related_product_id')
            line.complementary_related_product_ids = complementary_relations.mapped('related_product_id')

    # -------------------------------------------------------------------------
    # HELPERS: ALLOWED UOM
    # -------------------------------------------------------------------------
    def _get_allowed_sale_uoms(self):
        self.ensure_one()

        allowed_uoms = self.env['uom.uom']

        # Get product template - from either product_id or product_template_id
        if self.product_id:
            tmpl = self.product_id.product_tmpl_id
        elif self.product_template_id:
            tmpl = self.product_template_id
        else:
            return allowed_uoms

        # Package UoM = Native product UoM
        if tmpl.uom_id:
            allowed_uoms |= tmpl.uom_id

        # Product-specific unit ratio UoM only for sell_as = unit.
        if tmpl.sell_as == 'unit' and tmpl.package_uom_id:
            allowed_uoms |= tmpl.package_uom_id

        return allowed_uoms

    def _get_allowed_sale_uom_domain(self):
        self.ensure_one()
        return [('id', 'in', self._get_allowed_sale_uoms().ids)]

    # -------------------------------------------------------------------------
    # HELPERS: COMMISSION
    # -------------------------------------------------------------------------
    def _prepare_commission_values(self, product, order=None, product_uom=None, line_vals=None):
        order = order or self.order_id
        company = order.company_id if order else self.env.company

        if line_vals is not None:
            line_discount = line_vals.get('discount') or 0.0
            line_price_unit = line_vals.get('price_unit', 0.0)
            line_display_type = bool(line_vals.get('display_type'))
            line_is_downpayment = bool(line_vals.get('is_downpayment'))
            line_is_reward = bool(line_vals.get('is_reward_line'))
            line_is_eligible = (
                bool(product)
                and not line_display_type
                and not line_is_downpayment
                and line_discount <= 0.0
                and line_price_unit > 0.0
                and not line_is_reward
            )
        else:
            line_is_eligible = self._is_commission_eligible_line()

        if not company.enable_product_commission or not product or not line_is_eligible:
            return {
                'commission_percentage': 0.0,
                'commission_cost_snapshot': 0.0,
            }

        sale_uom = product_uom or self.product_uom or product.uom_id

        cost_in_sale_uom = product.uom_id._compute_price(
            product.standard_price or 0.0,
            sale_uom,
        )

        return {
            'commission_percentage': product.product_tmpl_id.commission_percentage or 0.0,
            'commission_cost_snapshot': cost_in_sale_uom,
        }

    def _apply_commission_values(self):
        for line in self:
            if line.product_id:
                vals = line._prepare_commission_values(
                    line.product_id,
                    line.order_id,
                    line.product_uom,
                )
            else:
                vals = {
                    'commission_percentage': 0.0,
                    'commission_cost_snapshot': 0.0,
                }

            line.update(vals)

    # -------------------------------------------------------------------------
    # HELPERS: MAX QTY PER ORDER / INVOICE
    # -------------------------------------------------------------------------
    def _check_max_qty_per_invoice(self):
        for order in self.mapped('order_id'):
            product_totals = defaultdict(float)

            valid_lines = order.order_line.filtered(
                lambda line: line.product_id and not line.display_type
            )

            for line in valid_lines:
                product = line.product_id.product_tmpl_id

                qty_in_base_uom = line.product_uom._compute_quantity(
                    line.product_uom_qty,
                    line.product_id.uom_id,
                )

                product_totals[product.id] += qty_in_base_uom

            for product_id, total_qty in product_totals.items():
                product = self.env['product.template'].browse(product_id)

                if product.max_qty_per_invoice and total_qty > product.max_qty_per_invoice:
                    if self.env.user.has_group('pharmacy_base.group_pharmacy_manager') or \
                       self.env.user.has_group('pharmacy_base.group_pharmacist'):
                        # Log the override immutably
                        self.env['pharmacy.audit.log'].sudo().create({
                            'user_id': self.env.user.id,
                            'model_name': 'sale.order',
                            'res_id': order.id,
                            'action_type': 'qty_override',
                            'old_value': str(product.max_qty_per_invoice),
                            'new_value': str(total_qty),
                            'note': _('Max Qty Overridden for product: %s') % product.name,
                        })
                    else:
                        raise ValidationError(
                            _(
                                'You cannot sell more than %(max_qty)s packages of %(product)s '
                                'in a single invoice/order.\n'
                                'Current total: %(current_total)s\n'
                                'Only a Pharmacist or Pharmacy Manager can override this limit.'
                            ) % {
                                'max_qty': product.max_qty_per_invoice,
                                'product': product.name,
                                'current_total': total_qty,
                            }
                        )

    @api.onchange('product_id', 'product_uom', 'product_uom_qty', 'price_unit', 'discount')
    def _onchange_commission_preview(self):
        self._apply_commission_values()
        self._compute_commission_fields()

    # -------------------------------------------------------------------------
    # CONSTRAINTS: SALE UOM
    # -------------------------------------------------------------------------
    @api.constrains('product_id', 'product_template_id', 'product_uom')
    def _check_sale_uom_allowed_for_product(self):
        for line in self:
            if not line.product_uom:
                continue

            allowed_uoms = line._get_allowed_sale_uoms()

            if allowed_uoms and line.product_uom not in allowed_uoms:
                product_name = (
                    line.product_id.display_name 
                    if line.product_id 
                    else line.product_template_id.display_name
                )
                raise ValidationError(
                    _(
                        'You can only sell "%(product)s" using its Package UoM '
                        'or its configured Unit Ratio UoM.\n'
                        'Allowed UoMs: %(allowed)s'
                    ) % {
                        'product': product_name,
                        'allowed': ', '.join(allowed_uoms.mapped('name')),
                    }
                )

    # -------------------------------------------------------------------------
    # ORM OVERRIDES: CREATE
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Product = self.env['product.product']
        SaleOrder = self.env['sale.order']
        Uom = self.env['uom.uom']

        for vals in vals_list:
            product_id = vals.get('product_id')
            if not product_id:
                continue

            # No commission for discounted/coupon/reward-like lines.
            if (vals.get('discount') or 0.0) > 0.0 or vals.get('price_unit', 0.0) <= 0.0:
                vals['commission_percentage'] = 0.0
                vals['commission_cost_snapshot'] = 0.0
                continue

            product = Product.browse(product_id)
            order = SaleOrder.browse(vals['order_id']) if vals.get('order_id') else False
            product_uom = Uom.browse(vals['product_uom']) if vals.get('product_uom') else product.uom_id

            prepared = self._prepare_commission_values(
                product,
                order,
                product_uom,
                line_vals=vals,
            )

            vals.setdefault(
                'commission_percentage',
                prepared['commission_percentage'],
            )
            vals.setdefault(
                'commission_cost_snapshot',
                prepared['commission_cost_snapshot'],
            )

        records = super().create(vals_list)
        records._check_max_qty_per_invoice()
        records.mapped('order_id.order_line')._compute_commission_fields()

        return records

    # -------------------------------------------------------------------------
    # ORM OVERRIDES: WRITE
    # -------------------------------------------------------------------------
    def write(self, vals):
        result = super().write(vals)

        if 'product_id' in vals or 'product_uom' in vals or 'discount' in vals or 'price_unit' in vals:
            self._sync_commission_snapshot_after_product_change()
            self.mapped('order_id.order_line')._compute_commission_fields()

        self._check_max_qty_per_invoice()

        return result

    # -------------------------------------------------------------------------
    # HELPERS: ORM POST-WRITE SYNC
    # -------------------------------------------------------------------------
    def _sync_commission_snapshot_after_product_change(self):
        """Re-compute commission snapshot after product or UoM change"""
        self._apply_commission_values()

    @api.onchange('product_id', 'product_template_id')
    def _onchange_product_pharmacy_logic(self):
        for line in self:
            product = line.product_id
            tmpl = product.product_tmpl_id if product else line.product_template_id

            if not tmpl:
                return {}

            package_uom = tmpl.uom_id
            ratio_uom = tmpl.package_uom_id if tmpl.sell_as == 'unit' else False

            allowed_uoms = self.env['uom.uom']
            if package_uom:
                allowed_uoms |= package_uom
            if ratio_uom:
                allowed_uoms |= ratio_uom

            line.x_package_uom_id = package_uom
            line.x_ratio_uom_id = ratio_uom
            line.x_sale_uom_readonly = (tmpl.sell_as == 'package')
            line.allowed_sale_uom_ids = [(6, 0, allowed_uoms.ids)]

            if tmpl.sell_as == 'package' and package_uom:
                line.product_uom = package_uom
            elif allowed_uoms and line.product_uom not in allowed_uoms:
                line.product_uom = package_uom

            line._apply_commission_values()
            line._compute_commission_fields()

            result = {
                'domain': {
                    'product_uom': [
                        '|',
                        ('id', '=', package_uom.id if package_uom else False),
                        ('id', '=', ratio_uom.id if ratio_uom else False),
                    ]
                }
            }

            if product and product.x_is_scheduled:
                result['warning'] = {
                    'title': _('Scheduled Medicine'),
                    'message': _('Warning: This product is a scheduled medicine.'),
                }

            return result
    def action_open_suggested_products_wizard(self):
        self.ensure_one()

        if not self.product_id:
            raise UserError(_('Please select a product first.'))

        product_tmpl = self.product_id.product_tmpl_id

        relations = self.env['product.related.product'].search([
            ('product_id', '=', product_tmpl.id),
            ('active', '=', True),
        ])

        if not relations:
            raise UserError(_('No suggested products found for this product.'))

        wizard = self.env['sale.order.suggested.products.wizard'].create({
            'sale_order_id': self.order_id.id,
            'sale_order_line_id': self.id,
            'product_id': self.product_id.id,
            'suggestion_line_ids': [
                (0, 0, {
                    'relation_type': rel.relation_type,
                    'related_product_tmpl_id': rel.related_product_id.id,
                    'priority': rel.priority,
                    'note': rel.note,
                })
                for rel in relations
            ],
        })

        return {
            'name': _('Suggested Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.suggested.products.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def _check_expired_lot_warning(self, vals):
        """
        If a lot is set on this line and the lot is expired,
        post a warning message on the sale order chatter and
        return a client warning action.
        """
        lot_id = vals.get('lot_id') or (self and self.lot_id and self.lot_id.id)
        if not lot_id:
            return False

        lot = self.env['stock.lot'].browse(lot_id)
        if not lot.exists():
            return False

        today = date.today()
        if lot.expiry_date and today > lot.expiry_date:
            return lot
        return False

    def action_confirm_expired_override(self, lot_id, order_id):
        """
        Called from JS after user clicks [Continue] on the warning dialog.
        Logs the override in the chatter.
        """
        lot = self.env['stock.lot'].browse(lot_id)
        order = self.env['sale.order'].browse(order_id)
        if order.exists():
            order.message_post(
                body=_(
                    "⚠️ Expired product warning overridden by %(user)s on %(dt)s.\n"
                    "Medicine: %(product)s — Lot: %(lot)s — Expiry: %(exp)s",
                    user=self.env.user.name,
                    dt=fields.Datetime.now(),
                    product=lot.product_id.display_name if lot else '',
                    lot=lot.name if lot else '',
                    exp=lot.expiry_date.strftime('%m/%Y') if (lot and lot.expiry_date) else '',
                )
            )
        return True