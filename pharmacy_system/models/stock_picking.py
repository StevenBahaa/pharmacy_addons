from odoo import models

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    # Logic moved to pharmacy_stock_expiry
