from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    

    is_consignment = fields.Boolean(
        string="Is Consignment", 
        default=False,
        tracking=True,
        index=True
        )