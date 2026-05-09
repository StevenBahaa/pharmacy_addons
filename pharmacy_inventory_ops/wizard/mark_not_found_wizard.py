from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MarkNotFoundWizard(models.TransientModel):
    """
    Bulk-mark selected count lines as 'Not Found'.
    """
    _name = 'pharmacy.count.not.found.wizard'
    _description = 'Mark Products as Not Found'

    count_id = fields.Many2one(
        comodel_name='pharmacy.count',
        string='Count',
        required=True,
    )
    line_ids = fields.Many2many(
        comodel_name='pharmacy.count.line',
        string='Lines to Mark',
    )
    reason = fields.Text(
        string='Reason',
        required=True,
        default=lambda self: _('Product not found during physical count'),
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Please select at least one line.'))
        for line in self.line_ids:
            line.write({
                'counted_status': 'not_found',
                'counted_qty': 0.0,
                'reason': self.reason,
            })
        return {'type': 'ir.actions.act_window_close'}
