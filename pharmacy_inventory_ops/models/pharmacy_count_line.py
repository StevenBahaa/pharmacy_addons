from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PharmacyCountLine(models.Model):
    """
    One product / location row inside a pharmacy inventory count.
    """
    _name = 'pharmacy.count.line'
    _description = 'Pharmacy Count Line'
    _order = 'sequence, product_id'

    # ------------------------------------------------------------------ #
    # Relations
    # ------------------------------------------------------------------ #
    count_id = fields.Many2one(
        comodel_name='pharmacy.count',
        string='Count',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        related='count_id.state',
        store=False
    )
    # ------------------------------------------------------------------ #
    # Product
    # ------------------------------------------------------------------ #
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
    )
    product_internal_ref = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        store=True,
    )
    product_barcode = fields.Char(
        string='Barcode',
        related='product_id.barcode',
        store=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
        related='product_id.uom_id',
        store=True,
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
    )

    # ------------------------------------------------------------------ #
    # Quantities
    # ------------------------------------------------------------------ #
    expected_qty = fields.Float(
        string='Expected Qty',
        digits='Product Unit of Measure',
        default=0.0,
    )
    counted_qty = fields.Float(
        string='Counted Qty',
        digits='Product Unit of Measure',
        default=False,   # False = not yet entered
    )
    difference = fields.Float(
        string='Difference',
        digits='Product Unit of Measure',
        compute='_compute_difference',
        store=True,
    )
    difference_value = fields.Monetary(
        string='Value of Difference',
        compute='_compute_difference',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='count_id.company_id.currency_id',
        string='Currency',
    )

    # ------------------------------------------------------------------ #
    # Status & reason
    # ------------------------------------------------------------------ #
    counted_status = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('counted', 'Counted'),
            ('not_found', 'Not Found'),
        ],
        string='Count Status',
        default='not_started',
        required=True,
        index=True,
    )
    reason = fields.Text(
        string='Reason',
        help='Mandatory when the counted quantity differs from the expected quantity.',
    )
    is_highlighted = fields.Boolean(
        string='Highlighted (barcode scan)',
        default=False,
        copy=False,
    )

    # ------------------------------------------------------------------ #
    # Computed
    # ------------------------------------------------------------------ #
    @api.depends('expected_qty', 'counted_qty', 'product_id')
    def _compute_difference(self):
        for line in self:
            if line.counted_qty is False or line.counted_qty is None:
                line.difference = 0.0
                line.difference_value = 0.0
            else:
                diff = line.counted_qty - line.expected_qty
                line.difference = diff
                cost = line.product_id.product_tmpl_id.public_price if line.product_id else 0.0
                line.difference_value = diff * cost

    # ------------------------------------------------------------------ #
    # Onchange – auto-fill expected qty from stock quants
    # ------------------------------------------------------------------ #
    # @api.onchange('product_id', 'location_id')
    # def _onchange_product_location(self):
    #     if self.product_id:
    #         location = (
    #             self.location_id
    #             or (self.count_id.warehouse_id.lot_stock_id if self.count_id.warehouse_id else False)
    #             or self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
    #         )
    #         if location:
    #             quant = self.env['stock.quant'].search([
    #                 ('product_id', '=', self.product_id.id),
    #                 ('location_id', '=', location.id),
    #             ], limit=1)
    #             self.expected_qty = quant.quantity if quant else 0.0
    #         else:
    #             self.expected_qty = 0.0
    @api.onchange('product_id')
    def _onchange_product_id_fill_expected(self):
        """Only fires in UI when user picks a product on a NEW line."""
        if not self.product_id:
            self.expected_qty = 0.0
            return
        self.expected_qty = self._get_current_stock_qty()
    @api.onchange('location_id')
    def _onchange_location_id_fill_expected(self):
        """Re-fills expected qty when location changes on a new line."""
        if not self.product_id:
            return
        self.expected_qty = self._get_current_stock_qty()
    def _get_current_stock_qty(self):
        """Return current on-hand qty for this product/location combination."""
        if not self.product_id:
            return 0.0
        location = self.location_id
        if not location and self.count_id.warehouse_id:
            location = self.count_id.warehouse_id.lot_stock_id
        domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id.usage', '=', 'internal'),
        ]
        if location:
            domain.append(('location_id', 'child_of', location.id))
        quants = self.env['stock.quant'].search(domain)
        return sum(quants.mapped('quantity'))
    def write(self, vals):
        """Protect expected_qty from being reset to 0 by UI re-renders."""
        if 'expected_qty' in vals and vals['expected_qty'] == 0.0:
            # Only allow setting to 0 if user explicitly cleared it
            # Filter out records that already have a real expected_qty
            protected = self.filtered(lambda l: l.expected_qty != 0.0)
            if protected:
                # Write without expected_qty for protected records
                super(PharmacyCountLine, protected).write(
                    {k: v for k, v in vals.items() if k != 'expected_qty'}
                )
                remaining = self - protected
                if remaining:
                    super(PharmacyCountLine, remaining).write(vals)
                return True
        return super().write(vals)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id') and vals.get('expected_qty', 0.0) == 0.0:
                # Re-fetch from stock to ensure correct value
                product = self.env['product.product'].browse(vals['product_id'])
                location_id = vals.get('location_id')
                domain = [
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal'),
                ]
                if location_id:
                    domain.append(('location_id', 'child_of', location_id))
                quants = self.env['stock.quant'].search(domain)
                qty = sum(quants.mapped('quantity'))
                if qty != 0.0:
                    vals['expected_qty'] = qty
        return super().create(vals_list)
    # ------------------------------------------------------------------ #
    # Counted qty write → update status
    # ------------------------------------------------------------------ #
    @api.onchange('counted_qty')
    def _onchange_counted_qty(self):
        if self.counted_qty is not False and self.counted_qty >= 0:
            self.counted_status = 'counted'
        elif self.counted_status == 'counted':
            self.counted_status = 'in_progress'

    # ------------------------------------------------------------------ #
    # Validation: reason mandatory for discrepancies
    # ------------------------------------------------------------------ #
    @api.constrains('counted_qty', 'reason', 'counted_status')
    def _check_reason_required(self):
        for line in self:
            if (
                line.counted_status == 'counted'
                and line.difference != 0
                and not line.reason
                and line.count_id.state == 'done'
            ):
                raise ValidationError(
                    _('Reason is required for "%s" because counted qty differs from expected.',
                      line.product_id.display_name)
                )

    # ------------------------------------------------------------------ #
    # Mark not found
    # ------------------------------------------------------------------ #
    def action_mark_not_found(self):
        for line in self:
            line.counted_status = 'not_found'
            line.counted_qty = 0.0
            if not line.reason:
                line.reason = _('Product not found during physical count')

    # ------------------------------------------------------------------ #
    # Reset line
    # ------------------------------------------------------------------ #
    def action_reset_line(self):
        for line in self:
            line.counted_qty = False
            line.counted_status = 'not_started'
            line.reason = False
            line.is_highlighted = False
