from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

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