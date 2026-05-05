from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_last_purchase_discount = fields.Float(
        string="Last Purchase Discount (%)",
        help="This field is automatically updated from the last validated vendor bill.",
        readonly=True,
    )
