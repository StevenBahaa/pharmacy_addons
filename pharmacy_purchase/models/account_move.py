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
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_consignment_payment_line = fields.Boolean(
        string='Consignment Payment Line',
        default=False,
        copy=False
    )

    def write(self, vals):
        if 'quantity' in vals:
            for line in self:
                if line.is_consignment_payment_line and line.move_id.is_consignment_bill and line.move_id.state != 'cancel':
                    raise UserError(
                        "You cannot change the quantity of a consignment bill line."
                    )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_consignment_payment(self):
        for line in self:
            if line.is_consignment_payment_line and line.move_id.is_consignment_bill and line.move_id.state != 'cancel':
                raise UserError("You cannot delete a consignment payment line.")