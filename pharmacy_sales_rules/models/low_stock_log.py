from odoo import fields, models


class LowStockLog(models.Model):
    _name = 'low.stock.log'
    _description = 'Low Stock Override Log'
    _order = 'date desc'

    user_id = fields.Many2one('res.users', required=True)
    product_id = fields.Many2one('product.product', required=True)
    quantity = fields.Float()
    stock_at_time = fields.Float()
    order_ref = fields.Char()
    source = fields.Selection([
        ('sale', 'Sales Order'),
        ('pos', 'POS Order'),
    ])
    date = fields.Datetime(default=fields.Datetime.now)

    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        store=True,
    )
