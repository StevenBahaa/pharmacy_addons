from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, time
from datetime import date
import calendar
import pytz
import re

class StockLot (models.Model):

    _inherit='stock.lot'

    x_expiry_month_year = fields.Char(
        string='Expiry Date (MM/YYYY)',
        help='Enter expiry date as MM/YYYY. The system will store it as the last day of that month.',
    )

    x_use_expiration_date = fields.Boolean(
        string='Use Expiration Date',
        compute='_compute_x_use_expiration_date',
        readonly=True,
    )

    @api.depends('product_id', 'product_id.use_expiration_date', 'product_id.tracking', 'product_id.product_tmpl_id.x_classification')
    def _compute_x_use_expiration_date(self):
        for rec in self:
            rec.x_use_expiration_date = (
                rec.product_id.use_expiration_date 
                and rec.product_id.tracking != 'none' 
                and rec.product_id.product_tmpl_id.x_classification == 'medicine'
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

    @api.depends('x_expiry_month_year')
    def _compute_expiry_date(self):
        for rec in self:
            rec.expiry_date = False

            if not rec.x_expiry_month_year:
                continue

            try:
                month, year = rec.x_expiry_month_year.split('/')
                month = int(month)
                year = int(year)

                last_day = calendar.monthrange(year, month)[1]
                rec.expiry_date = date(year, month, last_day)

            except Exception:
                rec.expiry_date = False

    @api.onchange('x_expiry_month_year')
    def _onchange_x_expiry_month_year(self):
        for lot in self:
            if lot.x_expiry_month_year:
                normalized_value = lot._normalize_month_year_value(
                    lot.x_expiry_month_year
                )
                lot.x_expiry_month_year = normalized_value

                expiry_datetime = lot._convert_month_year_value_to_expiration_datetime(
                    normalized_value
                )

                vals = lot._prepare_expiry_dates_from_expiration(
                    expiry_datetime,
                    lot.product_id,
                )

                lot.expiration_date = vals.get('expiration_date')
                lot.use_date = vals.get('use_date')
                lot.removal_date = vals.get('removal_date')
                lot.alert_date = vals.get('alert_date')
            else:
                lot.expiration_date = False
                lot.use_date = False
                lot.removal_date = False
                lot.alert_date = False



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
            raise ValidationError(
                _('Expiry Date must be in MM/YYYY format, for example 01/2026.')
            )

        month = int(match.group(1))
        year = int(match.group(2))

        return f'{month:02d}/{year}'


    def _convert_month_year_value_to_expiration_datetime(self, value):
        normalized_value = self._normalize_month_year_value(value)

        month_str, year_str = normalized_value.split('/')
        month = int(month_str)
        year = int(year_str)

        last_day = calendar.monthrange(year, month)[1]

        # End of selected month in user's timezone
        local_expiry_datetime = datetime.combine(
            datetime(year, month, last_day).date(),
            time(23, 59, 59)
        )

        user_tz_name = self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(user_tz_name)

        localized_expiry_datetime = user_tz.localize(local_expiry_datetime)

        # Odoo stores Datetime as UTC naive datetime
        utc_expiry_datetime = localized_expiry_datetime.astimezone(
            pytz.UTC
        ).replace(tzinfo=None)

        return utc_expiry_datetime
        

    def _prepare_expiry_dates_from_expiration(self , expiration_datetime, product):
        vals={
            'expiration_date': expiration_datetime,
            'use_date': expiration_datetime,
            'removal_date': expiration_datetime,
            'alert_date': expiration_datetime,
        }

        if product:
            product = product.product_tmpl_id

            if product.use_time:
                vals['use_date'] = expiration_datetime - relativedelta(days=product.use_time)

            if product.removal_time:
                vals['removal_date'] = expiration_datetime - relativedelta(days=product.removal_time)

            if product.alert_time:
                vals['alert_date'] = expiration_datetime - relativedelta(days=product.alert_time)
  
        return vals

    # --- دالة حساب حالة انتهاء الصلاحية ---
    @api.depends('expiration_date')
    def _compute_expiry_state(self):
            get_param = self.env['ir.config_parameter'].sudo().get_param
            near_limit = int(get_param('pharmacy_mgmt.near_expiry_limit', default=30))
            critical_limit = int(get_param('pharmacy_mgmt.critical_expiry_limit', default=7))
            
            today = datetime.now().date()
            for lot in self:
                if not lot.expiration_date:
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

        # --- منطق التحويل MM/YYYY الخاص بك ---
    @api.onchange('x_expiry_month_year')
    def _onchange_x_expiry_month_year(self):
            for lot in self:
                if lot.x_expiry_month_year:
                    normalized_value = lot._normalize_month_year_value(lot.x_expiry_month_year)
                    lot.x_expiry_month_year = normalized_value
                    expiry_datetime = lot._convert_month_year_value_to_expiration_datetime(normalized_value)
                    vals = lot._prepare_expiry_dates_from_expiration(expiry_datetime, lot.product_id)
                    
                    lot.expiration_date = vals.get('expiration_date')
                    lot.use_date = vals.get('use_date')
                    lot.removal_date = vals.get('removal_date')
                    lot.alert_date = vals.get('alert_date')
                else:
                    lot.expiration_date = False
                    lot.use_date = False
                    lot.removal_date = False
                    lot.alert_date = False

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
            month = int(match.group(1))
            year = int(match.group(2))
            return f'{month:02d}/{year}'

    def _convert_month_year_value_to_expiration_datetime(self, value):
            normalized_value = self._normalize_month_year_value(value)
            month_str, year_str = normalized_value.split('/')
            month, year = int(month_str), int(year_str)
            last_day = calendar.monthrange(year, month)[1]
            
            local_expiry_datetime = datetime.combine(datetime(year, month, last_day).date(), time(23, 59, 59))
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
    def _create_expiry_activities(self):
        """وظيفة آلية لفحص الأدوية وإنشاء تنبيهات للمدير"""
        user_to_notify = self.env.user  
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        
        critical_lots = self.search([('expiry_state', '=', 'critical')])
        
        for lot in critical_lots:
            existing_activities = self.env['mail.activity'].search([
                ('res_id', '=', lot.id),
                ('res_model_id', '=', self.env.ref('stock.model_stock_lot').id),
                ('summary', 'ilike', 'Expiry Alert')
            ])
            
            if not existing_activities:
                expiry_display = lot.x_expiry_month_year
                if not expiry_display and lot.expiration_date:
                    expiry_display = fields.Datetime.context_timestamp(
                        lot,
                        lot.expiration_date,
                    ).strftime('%m/%Y')

                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'res_id': lot.id,
                    'res_model_id': self.env.ref('stock.model_stock_lot').id,
                    'summary': f'Expiry Alert: {lot.product_id.display_name}',
                    'note': f'The product {lot.product_id.display_name} (Lot: {lot.name}) will expire very soon on {expiry_display or "N/A"}. Please take action.',
                    'user_id': user_to_notify.id,
                    'date_deadline': fields.Date.today(),
                })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            month_year = vals.get("x_expiry_month_year")
            if not month_year:
                continue

            vals["x_expiry_month_year"] = self._normalize_month_year_value(month_year)

            product = self.env["product.product"].browse(vals.get("product_id"))
            expiry_datetime = self._convert_month_year_value_to_expiration_datetime(
                vals["x_expiry_month_year"]
            )

            vals.update(
                self._prepare_expiry_dates_from_expiration(
                    expiry_datetime,
                    product,
                )
            )

        return super().create(vals_list)


    def write(self, vals):
        month_year = vals.get("x_expiry_month_year")
        if not month_year:
            return super().write(vals)

        normalized_month_year = self._normalize_month_year_value(month_year)

        for lot in self:
            expiry_datetime = lot._convert_month_year_value_to_expiration_datetime(
                normalized_month_year
            )

            expiry_vals = lot._prepare_expiry_dates_from_expiration(
                expiry_datetime,
                lot.product_id,
            )

            lot_vals = vals.copy()
            lot_vals["x_expiry_month_year"] = normalized_month_year
            lot_vals.update(expiry_vals)

            super(StockLot, lot).write(lot_vals)

        return True
