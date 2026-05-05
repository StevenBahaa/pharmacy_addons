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
       
       wizard = self.env['pharmacy.consignment.track.wizard'].create({
           'purchase_order_id': self.id,
           "line_ids" : [
            (0, 0, { 
                "purchase_order_line_id": line.id,  
                "product_id": line.product_id.id,  
                "received_qty": line.qty_received,  
                "sold_qty": 0,  # TODO: calculate based on stock.move lines
                "already_paid_qty": 0,  # TODO: implement payment tracking
                "payable_now_qty": 0,  # TODO: calculate
                "payable_remaining_qty": line.qty_received  # TODO: refine calculation
            })
            for line in self.order_line
            if line.product_id.type == 'product'     
           ]
       })

       return {
           "name": "Track Consignment Stock",
           "type": "ir.actions.act_window",
           "res_model": "pharmacy.consignment.track.wizard",
           "view_mode": "form",
           "res_id": wizard.id,
           "target": "new",
       }