import io
import base64
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError


FILTER_LABELS = {
    'exp_30': 'Expiring_30days',
    'exp_60': 'Expiring_60days',
    'exp_90': 'Expiring_90days',
}

FILTER_DAYS = {
    'exp_30': 30,
    'exp_60': 60,
    'exp_90': 90,
}

FILTER_STRINGS = {
    'exp_30': 'Expiring in 30 Days',
    'exp_60': 'Expiring in 60 Days',
    'exp_90': 'Expiring in 90 Days',
}


class ExpiredExportWizard(models.TransientModel):
    _name = 'expired.export.wizard'
    _description = 'Export Near-Expiry Medicines to Excel'

    filter_type = fields.Selection(
        selection=[
            ('exp_30', 'Expiring in 30 Days'),
            ('exp_60', 'Expiring in 60 Days'),
            ('exp_90', 'Expiring in 90 Days'),
        ],
        string="Filter",
        required=True,
        default='exp_30',
    )

    file_data = fields.Binary(string="Download File", readonly=True)
    file_name = fields.Char(string="File Name", readonly=True)
    state = fields.Selection(
        [('choose', 'Choose'), ('get', 'Download')],
        default='choose',
    )

    preview_html = fields.Html(string="Preview", readonly=True, sanitize=False)
    record_count = fields.Integer(string="Records Found", readonly=True)

    filter_label = fields.Char(
        string="Exporting",
        readonly=True,
        compute='_compute_filter_label',
    )

    @api.depends('filter_type')
    def _compute_filter_label(self):
        for rec in self:
            rec.filter_label = FILTER_STRINGS.get(rec.filter_type, '')

    # ------------------------------------------------------------------ #
    #  Onchange: refresh preview whenever user changes the filter         #
    # ------------------------------------------------------------------ #

    @api.onchange('filter_type')
    def _onchange_filter_type(self):
        self._generate_preview()

    # ------------------------------------------------------------------ #
    #  Create: generate preview on first open                             #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._generate_preview()
        return records

    # ------------------------------------------------------------------ #
    #  Core helpers                                                        #
    # ------------------------------------------------------------------ #

    def _get_quants(self):
        days = FILTER_DAYS[self.filter_type]
        return self.env['stock.quant'].search([
            ('lot_id', '!=', False),
            ('expiring_days', '>=', 0),
            ('expiring_days', '<=', days),
            ('quantity', '>', 0),
            ('product_id.x_classification', '=', 'medicine'),
            ('location_id.is_expired_location', '!=', True),
            ('location_id.usage', '!=', 'expired'),
        ])

    def _generate_preview(self):
        quants = self._get_quants()
        self.record_count = len(quants)

        if not quants:
            self.preview_html = (
                '<p style="color:#999; padding:8px;">'
                'No records found for this filter.'
                '</p>'
            )
            return

        rows_html = ''
        for q in quants:
            expiry_str = q.lot_expiry_date.strftime('%m/%Y') if q.lot_expiry_date else ''
            rows_html += f"""
            <tr>
                <td style="padding:5px 8px; border:1px solid #e0c97a;">{q.barcode or ''}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a;">{q.product_id.display_name or ''}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a;">{q.lot_id.name or ''}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a; text-align:center;">{expiry_str}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a; text-align:center;">{q.expiring_days}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a; text-align:center;">{q.boxes_qty:.2f}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a; text-align:center;">{q.units_qty:.2f}</td>
                <td style="padding:5px 8px; border:1px solid #e0c97a;">{q.location_id.complete_name or ''}</td>
            </tr>"""

        self.preview_html = f"""
        <div style="max-height:350px; overflow-y:auto; border:1px solid #ddd; border-radius:4px;">
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <thead>
                <tr style="background:#F4A460; font-weight:bold;">
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Barcode</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Medicine Name</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Lot</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Expiry</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Days Left</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Package</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Remaining Units</th>
                    <th style="padding:6px 8px; border:1px solid #c8854a; position:sticky; top:0; background:#F4A460;">Location</th>
                </tr>
            </thead>
            <tbody style="background:#FFF3CD;">
                {rows_html}
            </tbody>
        </table>
        </div>"""

    # ------------------------------------------------------------------ #
    #  Export to Excel                                                     #
    # ------------------------------------------------------------------ #

    def action_export(self):
        self.ensure_one()
        quants = self._get_quants()

        if not quants:
            raise UserError(_("No near-expiry records found for this filter."))

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("xlsxwriter is not installed. Run: pip install xlsxwriter"))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Near-Expiry Medicines')

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#F4A460', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
        })
        amber_fmt = workbook.add_format({'bg_color': '#FFF3CD', 'border': 1})

        headers = [
            'Barcode', 'Medicine Name', 'Lot', 'Expiry Date',
            'Days Remaining', 'Package', 'Remaining Units', 'Location',
        ]
        col_widths = [16, 30, 20, 14, 14, 12, 14, 30]

        for col, (h, w) in enumerate(zip(headers, col_widths)):
            worksheet.write(0, col, h, header_fmt)
            worksheet.set_column(col, col, w)

        for row, q in enumerate(quants, start=1):
            expiry_str = q.lot_expiry_date.strftime('%m/%Y') if q.lot_expiry_date else ''
            worksheet.write(row, 0, q.barcode or '', amber_fmt)
            worksheet.write(row, 1, q.product_id.display_name or '', amber_fmt)
            worksheet.write(row, 2, q.lot_id.name or '', amber_fmt)
            worksheet.write(row, 3, expiry_str, amber_fmt)
            worksheet.write(row, 4, q.expiring_days, amber_fmt)
            worksheet.write(row, 5, q.boxes_qty, amber_fmt)
            worksheet.write(row, 6, q.units_qty, amber_fmt)
            worksheet.write(row, 7, q.location_id.complete_name or '', amber_fmt)

        workbook.close()
        output.seek(0)

        label = FILTER_LABELS.get(self.filter_type, self.filter_type)
        today_str = date.today().strftime('%Y-%m-%d')
        filename = f"{label}_{today_str}.xlsx"

        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': filename,
            'state': 'get',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }