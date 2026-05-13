from odoo import models

class StockLocation(models.Model):
    _inherit = 'stock.location'
    # Logic moved to pharmacy_stock_expiry
