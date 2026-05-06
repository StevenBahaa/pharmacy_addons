from odoo import models, fields, api

class ConsignmentPayment(models.Model):
    _name = "pharmacy.consignment.payment"
    _description = "Consignment Payment"
    _order = 'date desc'

    purchase_order_id = fields.Many2one(
        comodel_name= 'purchase.order', 
        string='Purchase Order',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    purchase_order_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        string='Purchase Order Line',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    consignment_stock_line_id = fields.Many2one(
        comodel_name='pharmacy.consignment.stock.line',
        string='Consignment Stock Line',
        ondelete='cascade',
        index=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lot/Batch',
        index=True,
    )

    expiry_date = fields.Date(
        string='Expiry Date',
        related='lot_id.expiry_date',
        store=True,
    )

    vendor_bill_id = fields.Many2one(
        comodel_name='account.move',
        string='Vendor Bill',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    vendor_bill_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Vendor Bill Line',
        ondelete='cascade',
    )

    billed_qty = fields.Float(
        string='Billed Qty',
        required=True,
    )

    # For backward compatibility if needed, but we'll use billed_qty
    quantity_paid = fields.Float(
        string='Quantity Paid',
        related='billed_qty',
        readonly=True,
    )

    date = fields.Date(
        string='Date',
        default=fields.Date.today(),
        required=True,
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        default=lambda self: self.env.user,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('paid', 'Billed'),
        ],
        string='State',
        compute='_compute_state',
        store=True,
        default='draft',
        tracking=True,
    )

    @api.depends('vendor_bill_id.state')
    def _compute_state(self):
        for record in self:
            if record.vendor_bill_id.state == 'posted':
                record.state = 'paid'
            else:
                record.state = 'draft'
    

    
    
