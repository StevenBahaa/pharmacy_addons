from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    

    is_consignment = fields.Boolean(
        string="Is Consignment", 
        default=False,
        tracking=True,
        index=True
        )

    def action_open_consignment_tracking(self):
       self.ensure_one()
       return True  # placeholder for now