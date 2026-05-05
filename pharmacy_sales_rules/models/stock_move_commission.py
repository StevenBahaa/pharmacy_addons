import logging

from odoo import fields, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    commission_entry_created = fields.Boolean(
        string='Commission Entry Created',
        default=False,
        copy=False,
    )

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        res._create_commission_entry_from_move()
        return res

    def _create_commission_entry_from_move(self):
        CommissionEntry = self.env['sale.commission.entry']

        for move in self:
            if not move._should_create_commission_entry():
                continue

            vals = move._prepare_commission_entry_vals()
            if not vals:
                continue

            _logger.info(
                "Creating commission entry for move %s with vals: %s",
                move.id,
                vals,
            )
            CommissionEntry.sudo().create(vals)
            move.commission_entry_created = True

    def _should_create_commission_entry(self):
        self.ensure_one()

        if self.commission_entry_created:
            return False
        if self.state != 'done':
            return False
        if not self.sale_line_id:
            return False

        order = self.sale_line_id.order_id
        if not order.company_id.enable_product_commission:
            return False

        qty = self.quantity or 0.0
        if qty <= 0:
            return False

        return True

    def _prepare_commission_entry_vals(self):
        self.ensure_one()

        sale_line = self.sale_line_id
        order = sale_line.order_id
        company = order.company_id

        calculation = self._prepare_commission_calculation_values()
        if not calculation:
            return {}

        if float_is_zero(
            calculation.get('commission_amount', 0.0),
            precision_rounding=order.currency_id.rounding,
        ):
            return {}

        return {
            'sale_order_id': order.id,
            'sale_order_line_id': sale_line.id,
            'picking_id': self.picking_id.id if self.picking_id else False,
            'stock_move_id': self.id,
            'salesperson_id': order.user_id.id,
            'customer_id': order.partner_id.id,
            'product_id': self.product_id.id,
            'company_id': company.id,
            'currency_id': order.currency_id.id,
            'date': self.date or fields.Datetime.now(),
            'entry_type': calculation['entry_type'],
            'quantity': calculation['signed_qty'],
            'unit_sale_price': calculation['unit_sale_price'],
            'unit_cost': calculation['unit_cost'],
            'unit_margin': calculation['unit_margin'],
            'commission_percentage': calculation['commission_percentage'],
            'margin_base': calculation['margin_base'],
            'commission_amount': calculation['commission_amount'],
            'note': f'Auto-created from stock move {self.reference or self.id}',
        }

    def _prepare_commission_calculation_values(self):
        self.ensure_one()

        sale_line = self.sale_line_id
        move_qty = self.quantity or 0.0
        if move_qty <= 0:
            return {}

        source_uom = self.product_uom or self.product_id.uom_id
        target_uom = sale_line.product_uom or self.product_id.uom_id
        qty_in_sale_uom = source_uom._compute_quantity(move_qty, target_uom)

        commission_percentage = sale_line.commission_percentage or 0.0
        unit_sale_price = sale_line.price_unit * (
            1 - (sale_line.discount or 0.0) / 100.0
        )
        unit_cost = sale_line.commission_cost_snapshot or 0.0
        unit_margin = max(unit_sale_price - unit_cost, 0.0)

        entry_type = 'delivery'
        signed_qty = qty_in_sale_uom
        if self._is_return_commission_move():
            entry_type = 'return'
            signed_qty = -qty_in_sale_uom

        margin_base = unit_margin * signed_qty
        commission_amount = margin_base * (commission_percentage / 100.0)

        return {
            'entry_type': entry_type,
            'signed_qty': signed_qty,
            'unit_sale_price': unit_sale_price,
            'unit_cost': unit_cost,
            'unit_margin': unit_margin,
            'commission_percentage': commission_percentage,
            'margin_base': margin_base,
            'commission_amount': commission_amount,
        }

    def _is_return_commission_move(self):
        self.ensure_one()
        return bool(
            self.picking_id
            and self.picking_id.picking_type_id.code == 'incoming'
            and self.origin_returned_move_id
        )
