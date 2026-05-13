from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, date
import calendar
import pytz
import re

class StockLot(models.Model):
    _inherit = 'stock.lot'

    x_expiry_month_year = fields.Char(
        string='Expiry Date (MM/YYYY)',
        help='Enter expiry date as MM/YYYY. The system will store it as the last day of that month.',
        compute='_compute_x_expiry_month_year',
        inverse='_inverse_x_expiry_month_year',
        store=True,
    )

    expiry_date = fields.Date(
        string="Expiry Date",
        compute="_compute_expiry_date",
        store=True
    )

    expiry_state = fields.Selection([
        ('normal', 'Normal'),
        ('near', 'Near Expiry'),
        ('critical', 'Critical'),
        ('expired', 'Expired')
    ], string="Expiry State", compute="_compute_expiry_state", store=True)

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

    @api.depends('expiration_date')
    def _compute_x_expiry_month_year(self):
        for rec in self:
            if rec.expiration_date:
                # expiration_date is typically Datetime, but strftime works for both Date and Datetime
                rec.x_expiry_month_year = rec.expiration_date.strftime('%m/%Y')
            else:
                rec.x_expiry_month_year = False

    @api.depends('expiration_date')
    def _compute_expiry_date(self):
        for rec in self:
            if rec.expiration_date:
                rec.expiry_date = rec.expiration_date.date()
            else:
                rec.expiry_date = False

    def _inverse_x_expiry_month_year(self):
        for rec in self:
            if rec.x_expiry_month_year:
                normalized_value = rec._normalize_month_year_value(rec.x_expiry_month_year)
                expiry_datetime = rec._convert_month_year_value_to_expiration_datetime(normalized_value)
                vals = rec._prepare_expiry_dates_from_expiration(expiry_datetime, rec.product_id)
                rec.update(vals)
            else:
                rec.update({
                    'expiration_date': False,
                    'use_date': False,
                    'removal_date': False,
                    'alert_date': False
                })

    @api.depends('expiration_date', 'x_use_expiration_date')
    def _compute_expiry_state(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        near_limit = int(get_param('pharmacy_mgmt.near_expiry_limit', default=30))
        critical_limit = int(get_param('pharmacy_mgmt.critical_expiry_limit', default=7))
        today = date.today()
        for lot in self:
            if not lot.expiration_date or not lot.x_use_expiration_date:
                lot.expiry_state = 'normal'
                continue
            exp_date = lot.expiration_date.date()
            diff_days = (exp_date - today).days
            if diff_days < 0:
                lot.expiry_state = 'expired'
            elif diff_days <= critical_limit:
                lot.expiry_state = 'critical'
            elif diff_days <= near_limit:
                lot.expiry_state = 'near'
            else:
                lot.expiry_state = 'normal'

    @api.onchange('x_expiry_month_year')
    def _onchange_x_expiry_month_year(self):
        for lot in self:
            if lot.x_expiry_month_year:
                normalized_value = lot._normalize_month_year_value(lot.x_expiry_month_year)
                lot.x_expiry_month_year = normalized_value
                expiry_datetime = lot._convert_month_year_value_to_expiration_datetime(normalized_value)
                vals = lot._prepare_expiry_dates_from_expiration(expiry_datetime, lot.product_id)
                lot.update(vals)
            else:
                lot.update({
                    'expiration_date': False,
                    'use_date': False,
                    'removal_date': False,
                    'alert_date': False
                })

    @api.constrains('x_expiry_month_year')
    def _check_x_expiry_month_year(self):
        for lot in self:
            if lot.x_expiry_month_year:
                lot._normalize_month_year_value(lot.x_expiry_month_year)

    def _normalize_month_year_value(self, value):
        value = (value or '').strip()
        pattern = r'^(0?[1-9]|1[0-2])\/([0-9]{4})$'
        match = re.match(pattern, value)
        if not match:
            raise ValidationError(_('Expiry Date must be in MM/YYYY format, for example 01/2026.'))
        month, year = int(match.group(1)), int(match.group(2))
        return f'{month:02d}/{year}'

    def _convert_month_year_value_to_expiration_datetime(self, value):
        normalized_value = self._normalize_month_year_value(value)
        month_str, year_str = normalized_value.split('/')
        month, year = int(month_str), int(year_str)
        last_day = calendar.monthrange(year, month)[1]
        local_expiry_datetime = datetime.combine(date(year, month, last_day), time(23, 59, 59))
        user_tz_name = self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(user_tz_name)
        localized_expiry_datetime = user_tz.localize(local_expiry_datetime)
        return localized_expiry_datetime.astimezone(pytz.UTC).replace(tzinfo=None)

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

    @api.model
    def cron_detect_expired_lots(self):
        """وظيفة الفحص الليلي للمنتجات المنتهية - المدمجة"""
        if not self.env.su and not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("Only Inventory or Pharmacy Managers can run expiry detection manually."))
        
        today = fields.Date.context_today(self)
        expired_quants = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('lot_id.expiration_date', '<=', today),
            ('quantity', '>', 0)
        ])
        if expired_quants:
            # AUTO QUARANTINE: Transfer to expired location
            expired_quants.action_transfer_to_expired()
            self._notify_inventory_managers(expired_quants)
            self._create_expiry_activities(expired_quants)

    def _notify_inventory_managers(self, quants):
        ids_str = self.env['ir.config_parameter'].sudo().get_param('pharmacy_expiry.notification_recipients')
        if not ids_str:
            return
        user_ids = [int(i) for i in ids_str.split(',') if i.isdigit()]
        users = self.env['res.users'].browse(user_ids)
        if not users:
            return
        body_html = "<h3>Expired Medications Automatically Quarantined</h3><ul>"
        for quant in quants:
            body_html += f"<li><b>{quant.product_id.display_name}</b> - Lot: {quant.lot_id.name} - Qty: {quant.quantity} - Loc: {quant.location_id.display_name}</li>"
        body_html += "</ul><p>Please review the Expired Medicines dashboard.</p>"
        for user in users:
            if user.partner_id.email:
                mail_values = {
                    'subject': '⚠️ Pharmacy Alert: Expired Lots Quarantined',
                    'body_html': body_html,
                    'email_to': user.partner_id.email,
                    'email_from': self.env.company.catchall_email or self.env.user.email or 'admin@pharmacy.local',
                }
                self.env['mail.mail'].sudo().create(mail_values).send()

    def _create_expiry_activities(self, quants):
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        for quant in quants:
            quant.product_id.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("Expired lot detected: %s") % quant.lot_id.name,
                note=_("Lot was automatically quarantined. Please review."),
                user_id=self.env.user.id
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            month_year = vals.get("x_expiry_month_year")
            if not month_year:
                continue
            vals["x_expiry_month_year"] = self._normalize_month_year_value(month_year)
            product = self.env["product.product"].browse(vals.get("product_id"))
            expiry_datetime = self._convert_month_year_value_to_expiration_datetime(vals["x_expiry_month_year"])
            vals.update(self._prepare_expiry_dates_from_expiration(expiry_datetime, product))
        return super().create(vals_list)

    def write(self, vals):
        month_year = vals.get("x_expiry_month_year")
        if not month_year:
            return super().write(vals)
        normalized_month_year = self._normalize_month_year_value(month_year)
        for lot in self:
            expiry_datetime = lot._convert_month_year_value_to_expiration_datetime(normalized_month_year)
            expiry_vals = lot._prepare_expiry_dates_from_expiration(expiry_datetime, lot.product_id)
            lot_vals = vals.copy()
            lot_vals["x_expiry_month_year"] = normalized_month_year
            lot_vals.update(expiry_vals)
            super(StockLot, lot).write(lot_vals)
        return True
