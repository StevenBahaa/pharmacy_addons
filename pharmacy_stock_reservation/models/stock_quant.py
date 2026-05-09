from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)
class StockQuant(models.Model):
    _inherit = 'stock.quant'
    # ─── Reservation fields ───────────────────────────────────────────────────
    pharmacy_reserved_qty = fields.Float(
        string='Reserved Qty',
        digits='Product Unit of Measure',
        default=0.0,
        help='Units committed to confirmed (non-draft) transfer orders from this location.',
    )
    pharmacy_available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_pharmacy_available_qty',
        digits='Product Unit of Measure',
        store=True,
        help='On Hand minus Reserved — the quantity actually available for new transfers or sales.',
    )
    # ─── Computed fields ──────────────────────────────────────────────────────
    @api.depends('quantity', 'pharmacy_reserved_qty')
    def _compute_pharmacy_available_qty(self):
        for quant in self:
            quant.pharmacy_available_qty = quant.quantity - quant.pharmacy_reserved_qty
    # ─── Public API ───────────────────────────────────────────────────────────
    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None,
                                package_id=None, owner_id=None, strict=False,
                                allow_negative=False):
        """
        Override to return Available (on-hand minus reserved) instead of raw on-hand
        so that POS, sales orders, and new transfers all check the unreserved stock.
        """
        available = super()._get_available_quantity(
            product_id, location_id, lot_id=lot_id,
            package_id=package_id, owner_id=owner_id,
            strict=strict, allow_negative=allow_negative,
        )
        # Subtract pharmacy reservations held on this location
        reserved = self._get_pharmacy_reserved(product_id, location_id)
        return available - reserved
    @api.model
    def _get_pharmacy_reserved(self, product_id, location_id):
        """Return total pharmacy-reserved qty for product at location."""
        domain = [
            ('product_id', '=', product_id.id if hasattr(product_id, 'id') else product_id),
            ('location_id', '=', location_id.id if hasattr(location_id, 'id') else location_id),
        ]
        quants = self.search(domain)
        return sum(quants.mapped('pharmacy_reserved_qty'))
    def _reserve_quantity(self, qty, transfer_ref, user_id=None):
        """
        Reserve qty units on this quant for the given transfer reference.
        Raises UserError if available qty is insufficient.
        """
        self.ensure_one()
        available = self.quantity - self.pharmacy_reserved_qty
        if qty > available + 1e-9:  # float tolerance
            raise UserError(_(
                "Only %(avail).2f units available — %(res).2f are reserved for transfer %(ref)s.\n"
                "You cannot reserve %(req).2f units of %(product)s from %(location)s.",
                avail=available,
                res=self.pharmacy_reserved_qty,
                ref=transfer_ref or '',
                req=qty,
                product=self.product_id.display_name,
                location=self.location_id.display_name,
            ))
        self.pharmacy_reserved_qty += qty
        _logger.info(
            "RESERVATION: +%.2f %s @ %s for %s (total reserved: %.2f)",
            qty, self.product_id.display_name,
            self.location_id.display_name, transfer_ref,
            self.pharmacy_reserved_qty,
        )
    def _release_quantity(self, qty, transfer_ref, user_id=None):
        """Release reserved qty back to available."""
        self.ensure_one()
        release = min(qty, self.pharmacy_reserved_qty)
        self.pharmacy_reserved_qty = max(0.0, self.pharmacy_reserved_qty - release)
        _logger.info(
            "RELEASE: -%.2f %s @ %s for %s (total reserved: %.2f)",
            release, self.product_id.display_name,
            self.location_id.display_name, transfer_ref,
            self.pharmacy_reserved_qty,
        )
    @api.model
    def reserve_for_picking(self, picking):
        ReservationLog = self.env['pharmacy.reservation.log']
        for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            # sudo() ensures we can read all quants regardless of access rules
            quants = self.sudo().search([
                ('product_id', '=', move.product_id.id),
                ('location_id', 'child_of', move.location_id.id),
                ('quantity', '>', 0),
            ])
            _logger.info(
                "reserve_for_picking: move %s product %s location %s found %d quants",
                picking.name, move.product_id.display_name,
                move.location_id.display_name, len(quants)
            )
            remaining = move.product_uom_qty
            for quant in quants:
                if remaining <= 0:
                    break
                can_reserve = quant.quantity - quant.pharmacy_reserved_qty
                to_reserve = min(remaining, can_reserve)
                if to_reserve > 0:
                    quant.sudo()._reserve_quantity(to_reserve, picking.name)
                    remaining -= to_reserve
            if remaining > 1e-9:
                self.sudo().release_for_picking(picking)
                total_available = sum(
                    max(0, q.quantity - q.pharmacy_reserved_qty)
                    for q in self.sudo().search([
                        ('product_id', '=', move.product_id.id),
                        ('location_id', 'child_of', move.location_id.id),
                    ])
                )
                reserved_refs = self._get_conflicting_transfers(move.product_id, move.location_id)
                raise UserError(_(
                    "Cannot confirm transfer %(picking)s.\n\n"
                    "Product: %(product)s\n"
                    "Requested: %(req).2f %(uom)s\n"
                    "Available: %(avail).2f %(uom)s\n"
                    "%(reserved_info)s\n\n"
                    "Please reduce the quantity or cancel a conflicting transfer.",
                    picking=picking.name,
                    product=move.product_id.display_name,
                    req=move.product_uom_qty,
                    avail=total_available,
                    uom=move.product_uom.name,
                    reserved_info=reserved_refs,
                ))
            ReservationLog.sudo().create({
                'picking_id': picking.id,
                'product_id': move.product_id.id,
                'location_id': move.location_id.id,
                'reserved_qty': move.product_uom_qty - remaining,
                'action': 'reserve',
                'user_id': self.env.uid,
                'notes': f'Auto-reserved on transfer confirmation ({picking.name})',
            })
    @api.model
    def release_for_picking(self, picking):
        ReservationLog = self.env['pharmacy.reservation.log']
        for move in picking.move_ids.filtered(lambda m: m.state not in ('done',)):
            quants = self.sudo().search([
                ('product_id', '=', move.product_id.id),
                ('location_id', 'child_of', move.location_id.id),
                ('pharmacy_reserved_qty', '>', 0),
            ])
            released = 0.0
            remaining = move.product_uom_qty
            for quant in quants:
                if remaining <= 0:
                    break
                to_release = min(remaining, quant.pharmacy_reserved_qty)
                quant.sudo()._release_quantity(to_release, picking.name)
                released += to_release
                remaining -= to_release
            if released > 0:
                ReservationLog.sudo().create({
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'location_id': move.location_id.id,
                    'reserved_qty': released,
                    'action': 'release',
                    'user_id': self.env.uid,
                    'notes': f'Released on picking state change ({picking.name})',
                })
    @api.model
    def _get_conflicting_transfers(self, product_id, location_id):
        """Return a human-readable string of transfers holding reservations."""
        pickings = self.env['stock.picking'].search([
            ('state', 'in', ('waiting', 'confirmed', 'assigned', 'ready')),
            ('move_ids.product_id', '=', product_id.id),
            ('move_ids.location_id', '=', location_id.id),
        ], limit=5)
        if not pickings:
            return ''
        refs = ', '.join(pickings.mapped('name'))
        return _("Reserved by: %s") % refs