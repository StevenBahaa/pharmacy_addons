from odoo import models, fields , api 
from odoo.exceptions import UserError



class AccountMove(models.Model):
    _inherit = 'account.move'

    is_consignment_bill = fields.Boolean(
        string='Consignment Bill', 
        default=False,
        copy=False
    )

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.move_type == 'in_invoice':
                for line in move.invoice_line_ids:
                    if line.product_id:
                        line.product_id.product_tmpl_id.write({
                            'x_last_purchase_discount': line.discount
                        })
            
            # Update billed_qty on consignment stock lines
            if move.is_consignment_bill and move.state == 'posted':
                payments = self.env['pharmacy.consignment.payment'].search([('vendor_bill_id', '=', move.id)])
                for payment in payments:
                    if payment.consignment_stock_line_id:
                        payment.consignment_stock_line_id.billed_qty += payment.billed_qty
        return res

    def button_draft(self):
        # If moving back to draft, we should ideally reduce billed_qty, 
        # but Odoo 18 might have different flows. For now, let's just handle posting.
        # Actually, let's handle it for consistency.
        for move in self:
            if move.is_consignment_bill and move.state == 'posted':
                payments = self.env['pharmacy.consignment.payment'].search([('vendor_bill_id', '=', move.id)])
                for payment in payments:
                    if payment.consignment_stock_line_id:
                        payment.consignment_stock_line_id.billed_qty -= payment.billed_qty
        return super().button_draft()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_consignment_payment_line = fields.Boolean(
        string='Consignment Payment Line',
        default=False,
        copy=False
    )

    def write(self, vals):
        protected_fields = ['quantity', 'price_unit', 'discount', 'product_id', 'account_id', 'partner_id']
        if any(f in vals for f in protected_fields):
            for line in self:
                if line.is_consignment_payment_line and line.move_id.is_consignment_bill and line.move_id.state != 'cancel':
                    raise UserError(
                        "You cannot change critical fields (quantity, price, discount, product, account, vendor) of a consignment bill line."
                    )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_consignment_payment(self):
        for line in self:
            if line.is_consignment_payment_line and line.move_id.is_consignment_bill and line.move_id.state != 'cancel':
                raise UserError("You cannot delete a consignment payment line from a consignment bill.")