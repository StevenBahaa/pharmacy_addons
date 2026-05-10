from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    commission_percentage = fields.Float(
        string='Commission %',
        digits=(16, 2),
        help='Commission percentage used to calculate margin-based commission on sales order lines.',
        groups="pharmacy_base.group_pricing_manager,pharmacy_base.group_pharmacy_manager",
    )
    commission_feature_enabled = fields.Boolean(
        string='Commission Feature Enabled',
        compute='_compute_commission_feature_enabled',
        default=lambda self: self.env.company.enable_product_commission,
    )
    price_history_ids = fields.One2many(
        'product.price.history',
        'product_id',
        string='Price History',
        groups="pharmacy_base.group_pricing_manager,pharmacy_base.group_pharmacy_manager",
    )
    max_qty_per_invoice = fields.Integer(
        string='Max package per Invoice',
        help='Hard limit on quantity per sale invoice - applies at all stock levels.',
    )
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

    @api.depends_context('company')
    def _compute_commission_feature_enabled(self):
        enabled = self.env.company.enable_product_commission
        for rec in self:
            rec.commission_feature_enabled = enabled

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

    @api.constrains('commission_percentage')
    def _check_commission_percentage(self):
        for rec in self:
            if rec.commission_percentage < 0 or rec.commission_percentage > 100:
                raise ValidationError(_('Commission % must be between 0 and 100.'))

    @api.constrains('max_qty_per_invoice')
    def _check_max_qty(self):
        for rec in self:
            if rec.max_qty_per_invoice < 0:
                raise ValidationError(_('Max Qty must be positive'))

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

    @api.onchange('activate_stock_low')
    def _onchange_activate_stock_low(self):
        for rec in self:
            if rec.activate_stock_low:
                rec.max_qty_per_invoice = 0
            else:
                rec.low_stock_limit = 0
                rec.max_qty_low_stock = 0

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
                    body=_('Price changed: %(old)s -> %(new)s') % {
                        'old': old_price,
                        'new': rec.public_price,
                    }
                )

    def write(self, vals):
        old_prices = self._prepare_old_public_prices(vals)
        res = super().write(vals)
        self._create_public_price_history(old_prices, vals)
        return res