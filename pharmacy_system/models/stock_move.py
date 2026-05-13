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

    # -------------------------------------------------------------------------
    # HELPERS: INCOMING LOT REMAINING QUANTITY UX
    # -------------------------------------------------------------------------
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

        # Do not disturb Odoo's initial blank line before the user starts
        # encoding a lot/expiry split.
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
        }

    def _pharmacy_remove_remaining_lot_lines(self, lines):
        self.ensure_one()

        if lines:
            self.move_line_ids = self.move_line_ids - lines


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_expiry_month_year = fields.Char(
        string='Expiry Date (MM/YYYY)',
        help='Enter expiry date as MM/YYYY. The system will store it as the last day of that month on the lot.',
        compute='_compute_x_expiry_month_year',
        store=True,
        readonly=False,
    )

    @api.depends('lot_id', 'lot_id.x_expiry_month_year', 'quant_id', 'quant_id.lot_id.x_expiry_month_year')
    def _compute_x_expiry_month_year(self):
        for line in self:
            if line.lot_id and line.lot_id.x_expiry_month_year:
                line.x_expiry_month_year = line.lot_id.x_expiry_month_year
            elif line.quant_id and line.quant_id.lot_id and line.quant_id.lot_id.x_expiry_month_year:
                line.x_expiry_month_year = line.quant_id.lot_id.x_expiry_month_year

    x_product_tracking = fields.Selection(
        related='product_id.tracking',
        string='Product Tracking',
        readonly=True,
    )

    x_picking_code = fields.Selection(
        related='picking_id.picking_type_id.code',
        string='Picking Code',
        readonly=True,
    )

    x_use_expiration_date = fields.Boolean(
        compute='_compute_x_use_expiration_date',
        string='Use Expiration Date',
        readonly=True,
    )

    @api.depends('product_id', 'product_id.use_expiration_date', 'product_id.tracking', 'product_id.product_tmpl_id.x_classification')
    def _compute_x_use_expiration_date(self):
        for line in self:
            line.x_use_expiration_date = (
                line.product_id.use_expiration_date 
                and line.product_id.tracking != 'none' 
                and line.product_id.product_tmpl_id.x_classification == 'medicine'
            )

    def _normalize_expiry_month_year(self, expiry_month_year):
        if not expiry_month_year:
            return False

        value = expiry_month_year.strip()

        try:
            month_str, year_str = value.split('/')
            month = int(month_str)
            year = int(year_str)
        except Exception:
            raise ValidationError(_('Expiry Date must be in MM/YYYY format. Example: 05/2027'))

        if month < 1 or month > 12:
            raise ValidationError(_('Expiry month must be between 01 and 12.'))

        if year < 1900:
            raise ValidationError(_('Expiry year is not valid.'))

        today = fields.Date.context_today(self)
        current_month_start = today.replace(day=1)
        entered_month_start = datetime(year, month, 1).date()

        # if entered_month_start < current_month_start:
        #     raise ValidationError(_('Expiry Date cannot be in a past month or year.'))

        return f'{month:02d}/{year}'

    @api.onchange('x_expiry_month_year')
    def _onchange_x_expiry_month_year(self):
        for line in self:
            if line.x_expiry_month_year:
                line.x_expiry_month_year = line._normalize_expiry_month_year(
                    line.x_expiry_month_year
            )

    @api.onchange('lot_id')
    def _onchange_lot_id_expiry(self):
        for line in self:
            if line.lot_id and line.lot_id.x_expiry_month_year:
                line.x_expiry_month_year = line.lot_id.x_expiry_month_year

    @api.constrains('x_expiry_month_year')
    def _check_x_expiry_month_year(self):
        for line in self:
            if line.x_expiry_month_year:
                line._normalize_expiry_month_year(line.x_expiry_month_year)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('x_expiry_month_year'):
                vals['x_expiry_month_year'] = self._normalize_expiry_month_year(
                    vals['x_expiry_month_year']
                )

        lines = super().create(vals_list)

        for line in lines:
            if line.x_expiry_month_year and line.lot_id:
                line._apply_expiry_month_year_to_lot()

        return lines

    def write(self, vals):
        if vals.get('x_expiry_month_year'):
            vals['x_expiry_month_year'] = self._normalize_expiry_month_year(
                vals['x_expiry_month_year']
            )

        res = super().write(vals)

        if 'x_expiry_month_year' in vals or 'lot_id' in vals:
            for line in self:
                if line.x_expiry_month_year and line.lot_id:
                    line._apply_expiry_month_year_to_lot()

        return res

    def _action_done(self):
        res = super()._action_done()

        for line in self:
            if line.x_expiry_month_year and line.lot_id:
                line._apply_expiry_month_year_to_lot()

        return res

    def _apply_expiry_month_year_to_lot(self):
        self.ensure_one()

        if not self.x_expiry_month_year or not self.lot_id:
            return

        normalized_value = self._normalize_expiry_month_year(
            self.x_expiry_month_year
        )

        expiry_datetime = self._convert_month_year_value_to_expiration_datetime(
            normalized_value
        )

        expiry_vals = self._prepare_expiry_dates_from_expiration(
            expiry_datetime,
            self.product_id,
        )

        expiry_vals['x_expiry_month_year'] = normalized_value

        self.lot_id.write(expiry_vals)

    def _validate_month_year(self, value):
        value = (value or '').strip()

        pattern = r'^(0?[1-9]|1[0-2])\/([0-9]{4})$'
        match = re.match(pattern, value)

        if not match:
            raise ValidationError(
                _('Expiry Date must be in MM/YYYY format, for example 01/2026.')
            )

        return True

    def _convert_month_year_value_to_expiration_datetime(self, month_year):
        if not month_year:
            return False

        try:
            month_str, year_str = month_year.split('/')
            month = int(month_str)
            year = int(year_str)
        except Exception:
            raise ValidationError(_("Expiry Date must be in MM/YYYY format."))

        if month < 1 or month > 12:
            raise ValidationError(_("Month must be between 01 and 12."))

        last_day = calendar.monthrange(year, month)[1]

        # Local end of selected month
        local_expiry_dt = datetime.combine(
            datetime(year, month, last_day).date(),
            time(23, 59, 59)
        )

        # Convert user's local datetime to UTC because Odoo stores Datetime in UTC
        user_tz_name = self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(user_tz_name)

        local_expiry_dt = user_tz.localize(local_expiry_dt)
        utc_expiry_dt = local_expiry_dt.astimezone(pytz.UTC).replace(tzinfo=None)

        return utc_expiry_dt

    def _prepare_expiry_dates_from_expiration(self, expiration_datetime, product):
        vals = {
            'expiration_date': expiration_datetime,
            'use_date': expiration_datetime,
            'removal_date': expiration_datetime,
            'alert_date': expiration_datetime,
        }

        if product:
            product_tmpl = product.product_tmpl_id

            if product_tmpl.use_time:
                vals['use_date'] = expiration_datetime - relativedelta(days=product_tmpl.use_time)

            if product_tmpl.removal_time:
                vals['removal_date'] = expiration_datetime - relativedelta(days=product_tmpl.removal_time)

            if product_tmpl.alert_time:
                vals['alert_date'] = expiration_datetime - relativedelta(days=product_tmpl.alert_time)

        return vals
