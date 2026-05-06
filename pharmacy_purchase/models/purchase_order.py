from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_picking(self):
        res = super()._prepare_picking()
        if self.is_consignment:
            res['owner_id'] = self.partner_id.id
        return res

    

    is_consignment = fields.Boolean(
        string="Is Consignment", 
        default=False,
        tracking=True,
        index=True,
        help="If checked, this PO follows the consignment workflow."
    )

    def write(self, vals):
        if 'is_consignment' in vals:
            for order in self:
                if vals['is_consignment']:
                    order.message_post(body=f"PO marked as Consignment by {self.env.user.name} on {fields.Date.today()}")
                else:
                    order.message_post(body=f"Consignment status removed by {self.env.user.name}")
        return super().write(vals)


    def action_open_consignment_tracking(self):
        self.ensure_one()
        
        wizard_vals = {
            'purchase_order_id': self.id,
            'line_ids': [],
        }

        # Find all tracking lines for this PO
        cons_lines = self.env['pharmacy.consignment.stock.line'].search([
            ('purchase_order_id', '=', self.id)
        ])

        for line in cons_lines:
            # Find all payments (posted or draft) for this tracking line
            payments = self.env['pharmacy.consignment.payment'].search([
                ('consignment_stock_line_id', '=', line.id),
                ('vendor_bill_id.state', '!=', 'cancel')
            ])
            already_processed_qty = sum(payments.mapped('billed_qty'))
            
            payable_now_qty = max(line.sold_qty - already_processed_qty, 0.0)
            
            status = 'pending'
            if line.sold_qty > 0:
                if line.billed_qty >= line.sold_qty:
                    status = 'paid'
                elif line.billed_qty > 0 or already_processed_qty > 0:
                    status = 'partial'

            wizard_vals['line_ids'].append((0, 0, { 
                "consignment_stock_line_id": line.id,
                "purchase_order_line_id": line.purchase_order_line_id.id,  
                "product_id": line.product_id.id,  
                "lot_id": line.lot_id.id,
                "expiry_date": line.expiry_date,
                "received_qty": line.received_qty,  
                "sold_qty": line.sold_qty,  
                "already_billed_qty": line.billed_qty,  
                "payable_now_qty": payable_now_qty,  
                "remaining_qty": line.remaining_qty,
                "status": status,
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