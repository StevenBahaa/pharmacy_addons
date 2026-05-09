from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
class PharmacyForceUnreserveWizard(models.TransientModel):
    _name = 'pharmacy.force.unreserve.wizard'
    _description = 'Force Unreserve Stock — Inventory Manager'
    picking_id = fields.Many2one(
        'stock.picking', string='Transfer', required=True, readonly=True,
    )
    reason = fields.Text(
        string='Reason',
        required=True,
        help='Mandatory justification recorded in the audit log.',
    )
    line_ids = fields.One2many(
        'pharmacy.force.unreserve.wizard.line',
        'wizard_id',
        string='Lines to Unreserve',
    )
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        picking_id = self.env.context.get('default_picking_id')
        if not picking_id:
            return res
        picking = self.env['stock.picking'].browse(picking_id)
        StockQuant = self.env['stock.quant']
        lines = []
        for move in picking.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel')
        ):
            quants = StockQuant.sudo().search([
                ('product_id', '=', move.product_id.id),
                ('location_id', 'child_of', move.location_id.id),
                ('pharmacy_reserved_qty', '>', 0),
            ])
            reserved = sum(quants.mapped('pharmacy_reserved_qty'))
            # If quant has no reserved (reservation not written), fall back
            # to move qty so the wizard is still usable
            qty = reserved if reserved > 0 else move.reserved_availability or move.product_uom_qty
            lines.append((0, 0, {
                'product_id': move.product_id.id,
                'location_id': move.location_id.id,
                'reserved_qty': qty,
                'qty_to_unreserve': qty,
            }))
        res['line_ids'] = lines
        return res
    @api.constrains('reason')
    def _check_reason(self):
        for rec in self:
            if not rec.reason or len(rec.reason.strip()) < 10:
                raise ValidationError(
                    _("Please provide a meaningful reason (at least 10 characters) for the audit log.")
                )
    def action_force_unreserve(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'pharmacy_stock_reservation.group_pharmacy_inventory_manager'
        ):
            raise UserError(_("Only Inventory Managers can force-unreserve stock."))
        StockQuant = self.env['stock.quant'].sudo()
        ReservationLog = self.env['pharmacy.reservation.log']
        for line in self.line_ids:
            # We search for quants in the location or its children to match default_get logic
            quants = StockQuant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', 'child_of', line.location_id.id),
                ('pharmacy_reserved_qty', '>', 0),
            ])
            remaining = line.qty_to_unreserve
            for quant in quants:
                if remaining <= 0:
                    break
                to_release = min(remaining, quant.pharmacy_reserved_qty)
                quant._release_quantity(to_release, self.picking_id.name)
                remaining -= to_release
            ReservationLog.sudo().create({
                'picking_id': self.picking_id.id,
                'product_id': line.product_id.id,
                'location_id': line.location_id.id,
                'reserved_qty': line.qty_to_unreserve,
                'action': 'force_unreserve',
                'user_id': self.env.uid,
                'notes': f'[FORCE UNRESERVE] {self.reason}',
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reservation Released'),
                'message': _(
                    'Force unreserve applied. Audit log entry created.'
                ),
                'type': 'warning',
                'sticky': False,
            },
        }
class PharmacyForceUnreserveWizardLine(models.TransientModel):
    _name = 'pharmacy.force.unreserve.wizard.line'
    _description = 'Force Unreserve Wizard Line'
    wizard_id = fields.Many2one('pharmacy.force.unreserve.wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    reserved_qty = fields.Float(string='Currently Reserved', readonly=True,
                                digits='Product Unit of Measure')
    qty_to_unreserve = fields.Float(string='Qty to Unreserve',
                                    digits='Product Unit of Measure')
    @api.constrains('qty_to_unreserve', 'reserved_qty')
    def _check_qty(self):
        for line in self:
            if line.qty_to_unreserve <= 0:
                raise ValidationError(_("Quantity to unreserve must be positive."))
            if line.qty_to_unreserve > line.reserved_qty + 1e-9:
                raise ValidationError(_(
                    "Cannot unreserve more than the currently reserved quantity (%.2f)."
                ) % line.reserved_qty)
