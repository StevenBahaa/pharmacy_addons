from odoo import models, fields, api, _

class ConsignmentStockLine(models.Model):
    _name = 'pharmacy.consignment.stock.line'
    _description = 'Consignment Stock Tracking Line'
    _order = 'id desc'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, ondelete='cascade', index=True)
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line', required=True, ondelete='cascade', index=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', related='purchase_order_id.partner_id', store=True, index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', index=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch', index=True)
    expiry_date = fields.Date(string='Expiry Date', related='lot_id.expiry_date', store=True)
    
    received_qty = fields.Float(string='Received Qty', default=0.0, digits='Product Unit of Measure')
    sold_qty = fields.Float(string='Sold Qty', default=0.0, digits='Product Unit of Measure')
    billed_qty = fields.Float(string='Billed Qty', default=0.0, digits='Product Unit of Measure', help="Quantity already included in POSTED vendor bills")
    returned_qty = fields.Float(string='Returned Qty', default=0.0, digits='Product Unit of Measure')
    
    remaining_qty = fields.Float(string='Remaining Qty', compute='_compute_remaining_qty', store=True, digits='Product Unit of Measure')
    
    state = fields.Selection([
        ('received', 'Received'),
        ('partially_sold', 'Partially Sold'),
        ('fully_sold', 'Fully Sold'),
        ('billed', 'Fully Billed'),
        ('returned', 'Returned'),
    ], string='State', compute='_compute_state', store=True, default='received')

    @api.depends('received_qty', 'sold_qty', 'returned_qty')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = line.received_qty - line.sold_qty - line.returned_qty

    @api.depends('received_qty', 'sold_qty', 'billed_qty', 'returned_qty')
    def _compute_state(self):
        for line in self:
            if line.returned_qty >= line.received_qty:
                line.state = 'returned'
            elif line.billed_qty >= line.sold_qty and line.sold_qty > 0:
                line.state = 'billed'
            elif line.sold_qty >= (line.received_qty - line.returned_qty) and line.received_qty > 0:
                line.state = 'fully_sold'
            elif line.sold_qty > 0:
                line.state = 'partially_sold'
            else:
                line.state = 'received'
