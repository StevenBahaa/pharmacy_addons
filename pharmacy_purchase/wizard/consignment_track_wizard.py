from odoo.exceptions import UserError
from odoo import models, fields, api

class ConsignmentTrackWizard(models.TransientModel):
    _name = "pharmacy.consignment.track.wizard"
    _description = "Consignment Track Stock Wizard"
    
    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    line_ids = fields.One2many(
        "pharmacy.consignment.track.wizard.line",
        "wizard_id",
        string="Lines",
    )

    def action_create_payment_bill(self):
        self.ensure_one()

        payable_lines = self.line_ids.filtered(lambda l: l.payable_now_qty > 0)
        if not payable_lines:
            raise UserError("There are no sold unpaid quantities to bill.")

        po = self.purchase_order_id

        invoice_lines = []
        for line in payable_lines:
            po_line = line.purchase_order_line_id

            invoice_lines.append((0, 0, {
                "product_id": line.product_id.id,
                "name": po_line.name or line.product_id.display_name,
                "quantity": line.payable_now_qty,
                "price_unit": po_line.price_unit,
                "purchase_line_id": po_line.id,
            }))

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": po.partner_id.id,
            "invoice_origin": po.name,
            "invoice_date": fields.Date.context_today(self),
            "invoice_line_ids": invoice_lines,
        })

        for line in payable_lines:
            self.env["pharmacy.consignment.payment"].create({
                "purchase_order_id": po.id,
                "purchase_order_line_id": line.purchase_order_line_id.id,
                "product_id": line.product_id.id,
                "vendor_bill_id": bill.id,
                "quantity_paid": line.payable_now_qty,
            })

        po.message_post(
            body=f"Consignment vendor bill {bill.name or bill.ref or bill.id} created for sold unpaid quantities."
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Vendor Bill",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": bill.id,
            "target": "current",
        }


class ConsignmentTrackWizardLine(models.TransientModel):
    _name = "pharmacy.consignment.track.wizard.line"
    _description = "Consignment Track Stock Wizard Line"
    
    wizard_id = fields.Many2one(
        comodel_name='pharmacy.consignment.track.wizard',
        required=True,
        ondelete='cascade',
    )

    purchase_order_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
    )
    
    received_qty = fields.Float(readonly=True)
    sold_qty = fields.Float(readonly=True)
    already_paid_qty = fields.Float(readonly=True)
    payable_now_qty = fields.Float(readonly=True)
    payable_remaining_qty = fields.Float(readonly=True)

    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('partial', 'Partial'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='pending',
    )
