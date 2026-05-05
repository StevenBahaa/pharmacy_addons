from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ExpiredTransferWizard(models.TransientModel):
    _name = 'expired.transfer.wizard'
    _description = 'Confirm Transfer of Expired Medicines'

    quant_ids = fields.Many2many(
        'stock.quant',
        string="Selected Lots",
    )

    lot_count = fields.Integer(
        string="Number of Lots",
        compute="_compute_lot_count",
    )

    @api.depends('quant_ids')
    def _compute_lot_count(self):
        for rec in self:
            rec.lot_count = len(rec.quant_ids)

    def action_confirm(self):
        if not self.quant_ids:
            raise UserError(_("No lots selected."))
        return self.quant_ids.action_transfer_to_expired()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
