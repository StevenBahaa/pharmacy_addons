from odoo import models
from datetime import datetime

class ShortageReportXlsx(models.AbstractModel):
    _name = 'report.pharmacy_reports.shortage_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Pharmacy Shortage XLSX Report'

    def generate_xlsx_report(self, workbook, data, lines):
        # Fetch ALL shortage records from the database, ignoring current UI filters
        all_shortages = self.env['pharmacy.shortage.line'].search([], order='urgency_level desc, shortage_qty desc')
        
        sheet = workbook.add_worksheet('Master Shortage List')
        sheet.hide_gridlines(2)  # Hide gridlines for a cleaner look

        # --- Premium Color Palette ---
        NAVY = '#1F3864'
        SKY_BLUE = '#DDEBF7'
        WHITE = '#FFFFFF'
        CRITICAL_RED = '#FFC7CE'
        TEXT_DARK = '#212529'

        # --- Styles Definition ---
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
            'font_size': 10
        })
        
        row_style = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 9
        })

        row_alt_style = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 
            'bg_color': '#F9F9F9', 'font_size': 9
        })

        num_style = workbook.add_format({
            'border': 1, 'align': 'right', 'valign': 'vcenter', 
            'num_format': '#,##0.00', 'font_size': 9
        })

        critical_style = workbook.add_format({
            'border': 1, 'bg_color': CRITICAL_RED, 'font_color': '#9C0006',
            'align': 'center', 'bold': True, 'font_size': 9
        })

        # --- Header Section ---
        sheet.set_row(0, 30)
        sheet.write(0, 0, "PHARMACY INVENTORY SHORTAGE REPORT", title_style)
        
        sheet.write(1, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style)
        sheet.write(2, 0, f"Total Shortages Tracked: {len(all_shortages)}", info_style)

        # --- Table Headers (Row 5) ---
        headers = [
            'Product Name', 'Warehouse', 'Location', 
            'On Hand', 'Available', 'Min Qty', 
            'Incoming', 'Shortage', 'Urgency Level'
        ]
        
        START_ROW = 4
        for col, header in enumerate(headers):
            sheet.write(START_ROW, col, header, header_style)
            sheet.set_column(col, col, 15)

        sheet.set_column(0, 0, 45)  # Product name gets more space
        sheet.set_column(8, 8, 18)  # Urgency level space

        # --- Data Extraction & Injection ---
        row = START_ROW + 1
        for i, line in enumerate(all_shortages):
            style = row_alt_style if i % 2 == 0 else row_style
            
            sheet.write(row, 0, line.product_id.display_name, style)
            sheet.write(row, 1, line.warehouse_id.name or '-', style)
            sheet.write(row, 2, line.location_id.display_name or '-', style)
            
            sheet.write(row, 3, line.onhand_qty, num_style)
            sheet.write(row, 4, line.available_qty, num_style)
            sheet.write(row, 5, line.min_qty, num_style)
            sheet.write(row, 6, line.incoming_qty, num_style)
            sheet.write(row, 7, line.shortage_qty, num_style)
            
            # Urgency Badge Design
            urg_val = line.urgency_level
            urg_text = dict(line._fields['urgency_level'].selection).get(urg_val, 'Normal')
            
            if urg_val == 'critical':
                sheet.write(row, 8, urg_text.upper(), critical_style)
            else:
                sheet.write(row, 8, urg_text, style)
                
            row += 1

        # Freeze panes for easier scrolling
        sheet.freeze_panes(START_ROW + 1, 0)
