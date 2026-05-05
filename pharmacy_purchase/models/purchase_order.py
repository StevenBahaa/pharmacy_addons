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
        
        wizard_vals = {
            'purchase_order_id': self.id,
            'line_ids': [],
        }

        for line in self.order_line:
            if not line.product_id or line.product_id.type != 'consu':
                continue
                
            sold_qty = line._get_consignment_sold_qty_sales_only()
            already_paid_qty = line._get_consignment_already_paid_qty()
            payable_now_qty = max(sold_qty - already_paid_qty, 0.0)
            payable_remaining_qty = max(line.qty_received - sold_qty, 0.0)
            
            
            wizard_vals['line_ids'].append((0, 0, { 
                "purchase_order_line_id": line.id,  
                "product_id": line.product_id.id,  
                "received_qty": line.qty_received,  
                "sold_qty": sold_qty,  
                "already_paid_qty": already_paid_qty,  
                "payable_now_qty": payable_now_qty,  
                "payable_remaining_qty": payable_remaining_qty,
            }))

        wizard = self.env['pharmacy.consignment.track.wizard'].create(wizard_vals)   

        return {
            "name": "Track Consignment Stock",
            "type": "ir.actions.act_window",
            "res_model": "pharmacy.consignment.track.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }