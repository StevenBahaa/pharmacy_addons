from odoo import api, models
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.onchange(
        'move_line_ids',
        'product_uom_qty',
        'product_id',
        'product_uom',
        'picking_id',
    )
    def _onchange_pharmacy_sync_remaining_lot_line(self):
        for move in self:
            move._pharmacy_sync_remaining_lot_line()

    def _pharmacy_sync_remaining_lot_line(self):
        self.ensure_one()

        if not self._pharmacy_should_sync_remaining_lot_line():
            return

        move_lines = self.move_line_ids.filtered(
            lambda line: line.product_id == self.product_id
        )
        if not move_lines:
            return

        empty_lines = move_lines.filtered(
            lambda line: self._pharmacy_is_empty_remaining_lot_line(line)
        )
        filled_lines = move_lines - empty_lines
        if not filled_lines:
            return

        rounding = self._pharmacy_remaining_lot_rounding()
        filled_qty = sum(
            self._pharmacy_move_line_qty_in_move_uom(line)
            for line in filled_lines
        )
        remaining_qty = (self.product_uom_qty or 0.0) - filled_qty

        if float_compare(remaining_qty, 0.0, precision_rounding=rounding) <= 0:
            self._pharmacy_remove_remaining_lot_lines(empty_lines)
            return

        remaining_line = empty_lines[:1]
        duplicate_lines = empty_lines - remaining_line
        if duplicate_lines:
            self._pharmacy_remove_remaining_lot_lines(duplicate_lines)

        if remaining_line:
            self._pharmacy_update_remaining_lot_line(remaining_line, remaining_qty)
        else:
            self._pharmacy_add_remaining_lot_line(remaining_qty)

    def _pharmacy_should_sync_remaining_lot_line(self):
        self.ensure_one()

        picking_type = self.picking_id.picking_type_id or self.picking_type_id
        return bool(
            picking_type
            and picking_type.code == 'incoming'
            and self.product_id
            and self.product_id.tracking != 'none'
            and self.product_uom_qty
        )

    def _pharmacy_is_empty_remaining_lot_line(self, line):
        self.ensure_one()
        return bool(
            line.product_id == self.product_id
            and not line.lot_id
            and not line.lot_name
            and not line.x_expiry_month_year
        )

    def _pharmacy_remaining_lot_rounding(self):
        self.ensure_one()
        return (
            self.product_uom.rounding
            or self.product_id.uom_id.rounding
            or 0.01
        )

    def _pharmacy_move_line_qty_in_move_uom(self, line):
        self.ensure_one()

        quantity = line.quantity or 0.0
        line_uom = line.product_uom_id or self.product_uom
        move_uom = self.product_uom or line_uom
        if line_uom and move_uom and line_uom != move_uom:
            return line_uom._compute_quantity(quantity, move_uom, round=False)
        return quantity

    def _pharmacy_remaining_qty_in_line_uom(self, line, remaining_qty):
        self.ensure_one()

        line_uom = line.product_uom_id or self.product_uom
        move_uom = self.product_uom or line_uom
        if line_uom and move_uom and line_uom != move_uom:
            return move_uom._compute_quantity(remaining_qty, line_uom, round=False)
        return remaining_qty

    def _pharmacy_update_remaining_lot_line(self, line, remaining_qty):
        self.ensure_one()

        line_qty = self._pharmacy_remaining_qty_in_line_uom(line, remaining_qty)
        rounding = line.product_uom_id.rounding or self._pharmacy_remaining_lot_rounding()
        if float_compare(line.quantity or 0.0, line_qty, precision_rounding=rounding):
            line.quantity = line_qty
        if line.expiration_date:
            line.expiration_date = False

    def _pharmacy_add_remaining_lot_line(self, remaining_qty):
        self.ensure_one()

        vals = self._pharmacy_prepare_remaining_lot_line_vals(remaining_qty)
        new_line = self.env['stock.move.line'].new(vals)
        self.move_line_ids += new_line

    def _pharmacy_prepare_remaining_lot_line_vals(self, remaining_qty):
        self.ensure_one()
        return {
            'move_id': self.id,
            'picking_id': self.picking_id.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id or self.product_id.uom_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'lot_id': False,
            'lot_name': False,
            'expiration_date': False,
            'x_expiry_month_year': False,
            'quantity': remaining_qty,
            'owner_id': self.picking_id.owner_id.id if self.picking_id else False,
        }

    def _pharmacy_remove_remaining_lot_lines(self, lines):
        self.ensure_one()
        if lines:
            self.move_line_ids = self.move_line_ids - lines

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        res = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if self.picking_id and self.picking_id.owner_id:
            res['owner_id'] = self.picking_id.owner_id.id
        return res
