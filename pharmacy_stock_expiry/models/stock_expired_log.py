from odoo import models, fields, api
class StockExpiredLog(models.Model):
    _name = 'stock.expired.log'
    _description = 'Expired Stock Movement Log'

    product_id = fields.Many2one('product.product', required=True)
    qty = fields.Float(required=True)

    source_location_id = fields.Many2one('stock.location')
    dest_location_id = fields.Many2one('stock.location')

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)

    picking_id = fields.Many2one('stock.picking', string="Transfer")