from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    # ─── Summary fields shown on picking form ────────────────────────────────
    pharmacy_reservation_state = fields.Selection([
        ('none', 'No Reservation'),
        ('partial', 'Partially Reserved'),
        ('full', 'Fully Reserved'),
        ('released', 'Released'),
    ], string='Reservation State', compute='_compute_reservation_state', store=True)
    pharmacy_reserved_line_ids = fields.One2many(
        'pharmacy.reservation.log',
        'picking_id',
        string='Reservation Log',
    )
    has_pharmacy_reservation = fields.Boolean(
        compute='_compute_reservation_state',
        store=True,
    )
    # ─── Computed ─────────────────────────────────────────────────────────────
    @api.depends('state', 'move_ids.product_uom_qty')
    def _compute_reservation_state(self):
        StockQuant = self.env['stock.quant']
        for picking in self:
            if picking.state in ('draft', 'done', 'cancel'):
                picking.pharmacy_reservation_state = 'none'
                picking.has_pharmacy_reservation = False
                continue
            total_requested = 0.0
            total_covered = 0.0
            for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                total_requested += move.product_uom_qty
                reserved = StockQuant._get_pharmacy_reserved(
                    move.product_id, move.location_id
                )
                total_covered += min(move.product_uom_qty, reserved)
            if total_requested == 0:
                picking.pharmacy_reservation_state = 'none'
                picking.has_pharmacy_reservation = False
            elif total_covered >= total_requested - 1e-9:
                picking.pharmacy_reservation_state = 'full'
                picking.has_pharmacy_reservation = True
            elif total_covered > 0:
                picking.pharmacy_reservation_state = 'partial'
                picking.has_pharmacy_reservation = True
            else:
                picking.pharmacy_reservation_state = 'none'
                picking.has_pharmacy_reservation = False
    # ─── Lifecycle overrides ──────────────────────────────────────────────────
    def action_confirm(self):
        """
        On confirming a transfer (Draft → Confirmed/Waiting),
        immediately reserve stock for all outgoing moves.
        """
        result = super().action_confirm()
        outgoing = self.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state != 'draft'
        )
        StockQuant = self.env['stock.quant']
        for picking in outgoing:
            try:
                StockQuant.reserve_for_picking(picking)
            except UserError:
                # Re-raise — super() already changed state, so we reset
                picking.action_cancel()
                raise
        return result
    def action_assign(self):
        """
        action_assign (Check Availability) — also triggers reservation
        for transfers that were confirmed but had insufficient stock initially.
        """
        result = super().action_assign()
        outgoing = self.filtered(
            lambda p: p.picking_type_code == 'outgoing'
               and p.state in ('confirmed', 'assigned', 'ready')
               and not p.has_pharmacy_reservation
        )
        StockQuant = self.env['stock.quant']
        for picking in outgoing:
            StockQuant.reserve_for_picking(picking)
        return result
    def action_cancel(self):
        """Release all reservations before cancelling."""
        StockQuant = self.env['stock.quant']
        for picking in self:
            if picking.has_pharmacy_reservation:
                StockQuant.release_for_picking(picking)
        return super().action_cancel()
    def action_back_to_draft(self):
        """
        Revert to draft — must release reservations first.
        Odoo 18 uses _action_back_to_draft on picking; we hook both names.
        """
        StockQuant = self.env['stock.quant']
        for picking in self:
            if picking.has_pharmacy_reservation:
                StockQuant.release_for_picking(picking)
        return super().action_back_to_draft()
    def _action_back_to_draft(self):
        StockQuant = self.env['stock.quant']
        for picking in self:
            if picking.has_pharmacy_reservation:
                StockQuant.release_for_picking(picking)
        return super()._action_back_to_draft()
    def button_validate(self):
        """
        On validate (Done), release the reservation —
        the physical stock has moved, no longer needs to be locked.
        """
        StockQuant = self.env['stock.quant']
        for picking in self:
            if picking.has_pharmacy_reservation:
                StockQuant.release_for_picking(picking)
        return super().button_validate()
    # ─── Force unreserve action ───────────────────────────────────────────────
    def action_pharmacy_force_unreserve(self):
        """Open the Force Unreserve wizard (Inventory Manager only)."""
        self.ensure_one()
        if not self.env.user.has_group(
            'pharmacy_stock_reservation.group_pharmacy_inventory_manager'
        ):
            raise UserError(_("Only Inventory Managers can force-unreserve stock."))
        return {
            'name': _('Force Unreserve Stock'),
            'type': 'ir.actions.act_window',
            'res_model': 'pharmacy.force.unreserve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }
    # ─── Transfer confirmation popup ─────────────────────────────────────────
    def action_pharmacy_check_availability_popup(self):
        """Open the availability check wizard before confirming a transfer."""
        self.ensure_one()
        return {
            'name': _('Check Stock Availability'),
            'type': 'ir.actions.act_window',
            'res_model': 'pharmacy.transfer.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }