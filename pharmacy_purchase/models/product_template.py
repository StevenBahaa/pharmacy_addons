from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_last_purchase_discount = fields.Float(
        string="Last Purchase Discount (%)",
        help="This field is automatically updated from the last validated vendor bill.",
        readonly=True,
        groups="pharmacy_base.group_pricing_manager,pharmacy_base.group_pharmacy_manager",
    )

    discount_history_ids = fields.One2many(
        'product.discount.history',
        'product_tmpl_id',
        string="Discount History",
        groups="pharmacy_base.group_pricing_manager,pharmacy_base.group_pharmacy_manager",
    )
