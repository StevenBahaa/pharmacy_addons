from odoo import models, fields

class ProductDiscountHistory(models.Model):
    _name = 'product.discount.history'
    _description = 'Product Discount History'
    _order = 'date desc'

    product_tmpl_id = fields.Many2one('product.template', required=True)
    supplier_id = fields.Many2one('res.partner')
    invoice_id = fields.Many2one('account.move')
    discount = fields.Float()
    date = fields.Date()
