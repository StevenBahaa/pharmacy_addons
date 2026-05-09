from odoo import models, fields, api, _
from odoo.exceptions import UserError
class StockMove(models.Model):
    _inherit = 'stock.move'
    pharmacy_reserved_qty = fields.Float(
        string='Reserved Qty',
        digits='Product Unit of Measure',
        compute='_compute_pharmacy_reserved_qty',
        store=False,
        help='Qty currently locked from source location for this move line.',
    )
    pharmacy_available_qty = fields.Float(
        string='Available at Source',
        digits='Product Unit of Measure',
        compute='_compute_pharmacy_reserved_qty',
        store=False,
    )
    pharmacy_reservation_status = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved by other'),
        ('not_enough', 'Not Enough Stock'),
    ], compute='_compute_pharmacy_reserved_qty', store=False)
    @api.depends('product_id', 'location_id', 'product_uom_qty', 'state')
    def _compute_pharmacy_reserved_qty(self):
        StockQuant = self.env['stock.quant']
        for move in self:
            if not move.product_id or not move.location_id:
                move.pharmacy_reserved_qty = 0.0
                move.pharmacy_available_qty = 0.0
                move.pharmacy_reservation_status = 'available'
                continue
            quants = StockQuant.search([
                ('product_id', '=', move.product_id.id),
                ('location_id', '=', move.location_id.id),
            ])
            total_onhand = sum(quants.mapped('quantity'))
            total_reserved = sum(quants.mapped('pharmacy_reserved_qty'))
            available = total_onhand - total_reserved
            move.pharmacy_reserved_qty = total_reserved
            move.pharmacy_available_qty = available
            if available >= move.product_uom_qty - 1e-9:
                move.pharmacy_reservation_status = 'available'
            elif available > 0:
                move.pharmacy_reservation_status = 'reserved'
            else:
                move.pharmacy_reservation_status = 'not_enough'
    def _check_pharmacy_availability(self):
        """
        Called before confirming moves — raises if any move exceeds available qty.
        """
        for move in self:
            if move.location_id.usage != 'internal':
                continue
            StockQuant = self.env['stock.quant']
            available = StockQuant._get_available_quantity(
                move.product_id, move.location_id
            )
            if move.product_uom_qty > available + 1e-9:
                reserved_refs = StockQuant._get_conflicting_transfers(
                    move.product_id, move.location_id
                )
                raise UserError(_(
                    "Only %(avail).2f %(uom)s available for %(product)s at %(location)s — "
                    "%(req).2f %(uom)s requested.\n%(refs)s",
                    avail=available,
                    uom=move.product_uom.name,
                    product=move.product_id.display_name,
                    location=move.location_id.display_name,
                    req=move.product_uom_qty,
                    refs=reserved_refs,
                ))