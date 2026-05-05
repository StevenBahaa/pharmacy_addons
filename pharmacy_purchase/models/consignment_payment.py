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

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    vendor_bill_id = fields.Many2one(
        comodel_name='account.move',
        string='Vendor Bill',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    quantity_paid = fields.Float(
        string='Quantity Paid',
        required=True,
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
            ('paid', 'Paid'),
        ],
        string='State',
        default='draft',
        required=True,
        tracking=True,
    )

    def action_paid(self):
        self.write({'state': 'paid'})

    def action_cancel(self):
        self.write({'state': 'draft'})
    

    
    