import calendar
import re
from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    x_use_expiration_date = fields.Boolean(
        string='Use Pharmacy Expiry Date',
        compute='_compute_x_use_expiration_date',
        readonly=True,
    )

    @api.depends('product_id', 'product_id.use_expiration_date', 'product_id.tracking')
    def _compute_x_use_expiration_date(self):
        for rec in self:
            rec.x_use_expiration_date = (
                rec.product_id.use_expiration_date 
                and rec.product_id.tracking != 'none'
            )

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
        return res

    def _action_confirm(self, merge=False):
        for move in self:
            source = move.location_id
            dest = move.location_dest_id
            if source.is_expired_location:
                if not (dest.scrap_location or dest.is_expired_location):
                    raise UserError(
                        "You can only move stock from an Expired location to "
                        "a Scrap location or another Expired location."
                    )
        return super()._action_confirm(merge=merge)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_expiry_month_year = fields.Char(
        string='Expiry Date (MM/YYYY)',
        help='Enter expiry date as MM/YYYY. The system will store it as the last day of that month on the lot.',
        compute='_compute_x_expiry_month_year',
        store=True,
        readonly=False,
    )

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
        string='Use Pharmacy Expiry Date',
        compute='_compute_x_use_expiration_date',
        readonly=True,
    )

    @api.depends('product_id', 'product_id.use_expiration_date', 'product_id.tracking')
    def _compute_x_use_expiration_date(self):
        for rec in self:
            rec.x_use_expiration_date = (
                rec.product_id.use_expiration_date 
                and rec.product_id.tracking != 'none'
            )

    @api.depends('lot_id', 'lot_id.x_expiry_month_year')
    def _compute_x_expiry_month_year(self):
        for line in self:
            if line.lot_id and line.lot_id.x_expiry_month_year:
                line.x_expiry_month_year = line.lot_id.x_expiry_month_year
            elif line.quant_id and line.quant_id.lot_id and line.quant_id.lot_id.x_expiry_month_year:
                line.x_expiry_month_year = line.quant_id.lot_id.x_expiry_month_year

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
        local_expiry_dt = datetime.combine(
            datetime(year, month, last_day).date(),
            time(23, 59, 59),
        )

        user_tz_name = self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(user_tz_name)
        local_expiry_dt = user_tz.localize(local_expiry_dt)
        return local_expiry_dt.astimezone(pytz.UTC).replace(tzinfo=None)

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
