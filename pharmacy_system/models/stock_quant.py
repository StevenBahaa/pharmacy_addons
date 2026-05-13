from odoo import models

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    # Logic moved to pharmacy_stock_expiry
