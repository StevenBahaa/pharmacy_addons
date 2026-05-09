from odoo import models, fields, api, _
class PharmacyReservationLog(models.Model):
    _name = 'pharmacy.reservation.log'
    _description = 'Pharmacy Stock Reservation Audit Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'
    picking_id = fields.Many2one(
        'stock.picking', string='Transfer', ondelete='set null', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, index=True,
    )
    location_id = fields.Many2one(
        'stock.location', string='Source Location', required=True,
    )
    reserved_qty = fields.Float(
        string='Qty Affected', digits='Product Unit of Measure',
    )
    action = fields.Selection([
        ('reserve', 'Reserved'),
        ('release', 'Released'),
        ('force_unreserve', 'Force Unreserved'),
        ('revert_draft', 'Reverted to Draft'),
    ], string='Action', required=True)
    user_id = fields.Many2one(
        'res.users', string='By', default=lambda self: self.env.uid,
    )
    notes = fields.Text(string='Notes / Reason')
    create_date = fields.Datetime(string='Date/Time', readonly=True)
    display_name = fields.Char(compute='_compute_display_name')
    @api.depends('action', 'product_id', 'reserved_qty')
    def _compute_display_name(self):
        labels = {
            'reserve': _('Reserved'),
            'release': _('Released'),
            'force_unreserve': _('Force Unreserved'),
            'revert_draft': _('Draft Revert'),
        }
        for rec in self:
            action_label = labels.get(rec.action, rec.action)
            rec.display_name = f"{action_label} — {rec.product_id.display_name or ''} ({rec.reserved_qty:.2f})"