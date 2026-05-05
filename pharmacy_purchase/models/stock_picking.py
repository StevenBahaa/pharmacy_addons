from odoo import models, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.state == 'done' and picking.picking_type_id.code == 'outgoing' and picking.purchase_id and picking.purchase_id.is_consignment:
                # This is likely a return if it's an outgoing picking linked to a PO
                # In Odoo standard, returns create outgoing pickings with origin = PO Name
                picking.purchase_id.message_post(
                    body=_("Return transfer %s validated — Remaining Quantity updated") % picking.name
                )
        return res
