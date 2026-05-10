from odoo import models, fields, api
from datetime import timedelta

class ProductProduct(models.Model):
    _inherit = 'product.product'

    monthly_avg_consumption = fields.Float(string='Monthly Avg (3M)', compute='_compute_consumption_stats')
    forecast_need_3m = fields.Float(string='Forecast Need (3M)', compute='_compute_consumption_stats')
    coverage_ratio = fields.Float(string='Coverage Ratio %', compute='_compute_consumption_stats')

    def _compute_consumption_stats(self):
        three_months_ago = fields.Date.today() - timedelta(days=90)
        for product in self:
            moves = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '!=', 'internal'),
                ('date', '>=', three_months_ago)
            ])
            total_qty = sum(moves.mapped('product_uom_qty'))
            avg = total_qty / 3.0
            product.monthly_avg_consumption = avg
            product.forecast_need_3m = avg * 3
            
            if avg > 0:
                product.coverage_ratio = (product.qty_available / avg) * 100
            else:
                product.coverage_ratio = 100 if product.qty_available > 0 else 0