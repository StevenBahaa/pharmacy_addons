from odoo import models
from datetime import datetime


class ShortageReportXlsx(models.AbstractModel):
    _name = 'report.pharmacy_reports.shortage_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Pharmacy Shortage XLSX Report'

    def generate_xlsx_report(self, workbook, data, lines):
        if not self.env.user.has_group('pharmacy_base.group_purchasing_officer') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            from odoo.exceptions import AccessError
            from odoo import _
            raise AccessError(_("You are not authorized to export the Shortage Report."))

        # If called from the header button, 'data' contains the domain.
        # If called from the Actions menu with selected rows, 'lines' is used.
        if data and data.get('domain') is not None:
            all_shortages = self.env['pharmacy.shortage.line'].search(
                data['domain'],
                order='urgency_level desc, shortage_qty desc'
            )
        elif lines:
            all_shortages = lines
        else:
            all_shortages = self.env['pharmacy.shortage.line'].search(
                [], order='urgency_level desc, shortage_qty desc'
            )

        sheet = workbook.add_worksheet('Shortage Dashboard')
        sheet.hide_gridlines(2)

        # --- Premium Color Palette ---
        NAVY = '#1F3864'
        SKY_BLUE = '#DDEBF7'
        WHITE = '#FFFFFF'
        CRITICAL_RED = '#FFC7CE'
        WARNING_ORANGE = '#FFEB9C'
        COVERED_GREEN = '#C6EFCE'

        # --- Styles ---
        title_style = workbook.add_format({
            'bold': True, 'font_size': 18, 'font_color': NAVY,
            'align': 'left', 'valign': 'vcenter'
        })
        info_style = workbook.add_format({
            'font_size': 9, 'font_color': '#555555',
            'align': 'left', 'valign': 'vcenter'
        })
        header_style = workbook.add_format({
            'bold': True, 'bg_color': NAVY, 'font_color': WHITE,
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'font_size': 10, 'text_wrap': True
        })
        row_style = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 9
        })
        row_alt_style = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
            'bg_color': '#F2F7FF', 'font_size': 9
        })
        num_style = workbook.add_format({
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '#,##0.00', 'font_size': 9
        })
        num_alt_style = workbook.add_format({
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '#,##0.00', 'bg_color': '#F2F7FF', 'font_size': 9
        })
        critical_style = workbook.add_format({
            'border': 1, 'bg_color': CRITICAL_RED, 'font_color': '#9C0006',
            'align': 'center', 'bold': True, 'font_size': 9
        })
        warning_style = workbook.add_format({
            'border': 1, 'bg_color': WARNING_ORANGE, 'font_color': '#9C5700',
            'align': 'center', 'bold': True, 'font_size': 9
        })
        covered_style = workbook.add_format({
            'border': 1, 'bg_color': COVERED_GREEN, 'font_color': '#276221',
            'align': 'center', 'bold': True, 'font_size': 9
        })
        date_style = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': 'yyyy-mm-dd hh:mm', 'font_size': 9
        })
        date_alt_style = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': 'yyyy-mm-dd hh:mm', 'bg_color': '#F2F7FF', 'font_size': 9
        })

        # --- Filter label ---
        filter_label = data.get('filter_label', 'All Records') if data else 'All Records'
        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # --- Header Section ---
        sheet.set_row(0, 35)
        sheet.merge_range(0, 0, 0, 13, "PHARMACY SHORTAGE DASHBOARD EXPORT", title_style)
        sheet.write(1, 0, f"Generated on: {generated_at}", info_style)
        sheet.write(2, 0, f"Filter Applied: {filter_label}", info_style)
        sheet.write(2, 4, f"Total Records: {len(all_shortages)}", info_style)

        # --- Table Headers (Row 5) ---
        headers = [
            'Product', 'Warehouse', 'Location',
            'Min Qty', 'On Hand', 'Reserved',
            'Available', 'Incoming Qty', 'Incoming References',
            'Shortage Qty', 'Suggested Order', 'Status',
            'Urgency', 'Last Refresh'
        ]

        START_ROW = 4
        sheet.set_row(START_ROW, 30)
        for col, header in enumerate(headers):
            sheet.write(START_ROW, col, header, header_style)

        # Column widths
        col_widths = [40, 18, 22, 10, 10, 10, 10, 12, 35, 12, 14, 14, 14, 20]
        for col, w in enumerate(col_widths):
            sheet.set_column(col, col, w)

        # State/urgency label maps
        state_labels = dict(
            self.env['pharmacy.shortage.line']._fields['state'].selection
        )
        urgency_labels = dict(
            self.env['pharmacy.shortage.line']._fields['urgency_level'].selection
        )

        # --- Data rows ---
        row = START_ROW + 1
        for i, line in enumerate(all_shortages):
            is_alt = i % 2 == 0
            rs = row_alt_style if is_alt else row_style
            ns = num_alt_style if is_alt else num_style
            ds = date_alt_style if is_alt else date_style

            sheet.write(row, 0, line.product_id.display_name, rs)
            sheet.write(row, 1, line.warehouse_id.name or '-', rs)
            sheet.write(row, 2, line.location_id.display_name or '-', rs)
            sheet.write(row, 3, line.min_qty, ns)
            sheet.write(row, 4, line.onhand_qty, ns)
            sheet.write(row, 5, line.reserved_qty, ns)
            sheet.write(row, 6, line.available_qty, ns)
            sheet.write(row, 7, line.incoming_qty, ns)
            sheet.write(row, 8, line.incoming_reference_display or '-', rs)
            sheet.write(row, 9, line.shortage_qty, ns)
            sheet.write(row, 10, line.suggested_order_qty, ns)

            # Status badge
            state_text = state_labels.get(line.state, line.state)
            if line.state == 'to_order':
                sheet.write(row, 11, state_text, critical_style)
            elif line.state == 'partial':
                sheet.write(row, 11, state_text, warning_style)
            elif line.state == 'covered':
                sheet.write(row, 11, state_text, covered_style)
            else:
                sheet.write(row, 11, state_text, rs)

            # Urgency badge
            urg_text = urgency_labels.get(line.urgency_level, line.urgency_level)
            if line.urgency_level == 'critical':
                sheet.write(row, 12, urg_text, critical_style)
            elif line.urgency_level == 'warning':
                sheet.write(row, 12, urg_text, warning_style)
            else:
                sheet.write(row, 12, urg_text, rs)

            # Last refresh datetime
            if line.last_refresh_date:
                sheet.write_datetime(row, 13, line.last_refresh_date, ds)
            else:
                sheet.write(row, 13, '-', rs)

            row += 1

        sheet.freeze_panes(START_ROW + 1, 0)
        sheet.autofilter(START_ROW, 0, row - 1, len(headers) - 1)
