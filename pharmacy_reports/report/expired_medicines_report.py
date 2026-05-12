# -*- coding: utf-8 -*-
from odoo import models


class ExpiredMedicinesReport(models.AbstractModel):
    _name = 'report.pharmacy_reports.expired_medicines'
    _description = 'Expired Medicines Report'

    def _get_report_values(self, docids, data=None):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            from odoo.exceptions import AccessError
            from odoo import _
            raise AccessError(_("You are not authorized to view the Expired Medicines Report."))

        wizard = self.env['expired.medicines.report.wizard'].browse(docids)

        month = int(wizard.month)
        year = int(wizard.year)
        period = '%02d/%d' % (month, year)

        domain = [
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'expired'),
            ('removal_date', '!=', False),
        ]
        if wizard.location_ids:
            domain.append(('location_id', 'in', wizard.location_ids.ids))

        quants = self.env['stock.quant'].search(domain)
        quants = quants.filtered(
            lambda q: q.removal_date.month == month
            and q.removal_date.year == year
        ).sorted(key=lambda q: q.product_id.display_name)

        grouped = {}
        grand_total = 0.0

        is_pricing_manager = self.env.user.has_group('pharmacy_base.group_pricing_manager') or \
                             self.env.user.has_group('pharmacy_base.group_pharmacy_manager')

        for g in quants:
            loc = g.location_id
            product = g.product_id
            units_per_package = product.product_tmpl_id.units_per_package or 1
            total_units = round(g.quantity * units_per_package)
            box_qty = total_units // units_per_package
            unit_qty = total_units % units_per_package

            # Mask cost data if not pricing manager
            box_price = product.standard_price if is_pricing_manager else 0.0
            total_value = g.quantity * box_price if is_pricing_manager else 0.0
            grand_total += total_value

            if loc not in grouped:
                grouped[loc] = []
            grouped[loc].append({
                'barcode': product.barcode or '',
                'name': product.display_name,
                'lot': g.lot_id.name or '-',
                'expiry_date': g.removal_date.strftime('%m/%Y') if g.removal_date else '-',
                'box_qty': box_qty,
                'unit_qty': unit_qty,
                'box_price': box_price,
                'total_value': total_value,
            })
        grouped_lines = [
            {'location_name': loc.complete_name, 'lines': lines}
            for loc, lines in grouped.items()
        ]

        total_boxes = sum(l['box_qty'] for g in grouped_lines for l in g['lines'])
        total_units = sum(l['unit_qty'] for g in grouped_lines for l in g['lines'])

        return {
            'grouped_lines': grouped_lines,
            'grand_total': grand_total,
            'total_boxes': total_boxes,
            'total_units': total_units,
            'month': month,
            'year': year,
            'period': period,
        }
