import calendar
import logging
import re
import pytz
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models , api

from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    # FIELDS: COMMISSION
    # -------------------------------------------------------------------------
    commission_entry_created = fields.Boolean(
        string='Commission Entry Created',
        default=False,
        copy=False,
    )

    # -------------------------------------------------------------------------
    # STOCK FLOW OVERRIDES
    # -------------------------------------------------------------------------
    def _action_done(self, cancel_backorder=False):
        
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            for line in move.move_line_ids:
                source = line.location_id
                dest = line.location_dest_id
                if source.is_expired_location or dest.is_expired_location:
                    self.env['stock.expired.log'].create({
                        'product_id': line.product_id.id,
                        'qty': line.quantity,  
                        'source_location_id': source.id,
                        'dest_location_id': dest.id,
                        'picking_id': move.picking_id.id,
                        'user_id': self.env.user.id,
                        'date': fields.Datetime.now(),
                    })
        res._create_commission_entry_from_move()
        return res
    
    def _action_confirm(self, merge=False):
        for move in self:
            source = move.location_id
            dest = move.location_dest_id
            if source.is_expired_location:
                if not (dest.scrap_location or dest.is_expired_location):
                    raise UserError(
                        "❌ You can only move stock from an Expired location to "
                        "a Scrap location or another Expired location."
                    )
        return super()._action_confirm(merge=merge)

    # -------------------------------------------------------------------------
    # COMMISSION ENTRY CREATION
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # HELPERS: VALIDATION / ELIGIBILITY
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # HELPERS: PREPARE ENTRY VALUES
    # -------------------------------------------------------------------------
    def _prepare_commission_entry_vals(self):
        self.ensure_one()

        sale_line = self.sale_line_id
        order = sale_line.order_id
        company = order.company_id

        calculation = self._prepare_commission_calculation_values()
        if not calculation:
            return {}

        # Skip noise entries: do not create commission records with zero amount.
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

    # -------------------------------------------------------------------------
    # HELPERS: COMMISSION CALCULATION
    # -------------------------------------------------------------------------
    def _prepare_commission_calculation_values(self):
        self.ensure_one()

        sale_line = self.sale_line_id

        move_qty = self.quantity or 0.0
        if move_qty <= 0:
            return {}

        source_uom = self.product_uom or self.product_id.uom_id
        target_uom = sale_line.product_uom or self.product_id.uom_id

        qty_in_sale_uom = source_uom._compute_quantity(
            move_qty,
            target_uom,
        )

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

    # -------------------------------------------------------------------------
    # HELPERS: RETURN DETECTION
    # -------------------------------------------------------------------------
    def _is_return_commission_move(self):
        self.ensure_one()

        return bool(
            self.picking_id
            and self.picking_id.picking_type_id.code == 'incoming'
            and self.origin_returned_move_id
        )

