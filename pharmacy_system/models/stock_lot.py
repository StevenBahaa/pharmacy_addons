from odoo import models

class StockLot(models.Model):
    _inherit = 'stock.lot'
    # Logic moved to pharmacy_stock_expiry
