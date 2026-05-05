from odoo import models, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            if picking.purchase_id and picking.purchase_id.is_consignment:
                picking.owner_id = picking.purchase_id.partner_id
                # Force update existing moves if any
                picking.move_ids.write({'restrict_partner_id': picking.purchase_id.partner_id.id})
        return pickings

    def write(self, vals):
        res = super().write(vals)
        if 'purchase_id' in vals or 'owner_id' in vals:
            for picking in self:
                if picking.purchase_id and picking.purchase_id.is_consignment and not picking.owner_id:
                    picking.owner_id = picking.purchase_id.partner_id
                    picking.move_ids.write({'restrict_partner_id': picking.purchase_id.partner_id.id})
        return res

    def button_validate(self):
        # Ensure owner is set on all move lines before validation
        for picking in self:
            if picking.purchase_id and picking.purchase_id.is_consignment:
                if not picking.owner_id:
                    picking.owner_id = picking.purchase_id.partner_id
                for move in picking.move_ids:
                    move.move_line_ids.write({'owner_id': picking.owner_id.id})
        
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.state == 'done' and picking.picking_type_id.code == 'outgoing' and picking.purchase_id and picking.purchase_id.is_consignment:
                picking.purchase_id.message_post(
                    body=_("Return transfer %s validated — Remaining Quantity updated") % picking.name
                )
        return res

