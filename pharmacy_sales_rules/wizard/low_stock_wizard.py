from odoo import models, fields, api, _


class LowStockWarningWizard(models.TransientModel):
    _name = 'low.stock.warning.wizard'
    _description = 'Low Stock Warning Wizard'

    order_id = fields.Many2one('sale.order', required=True, readonly=True)
    line_ids = fields.One2many('low.stock.warning.line', 'wizard_id')

    def action_confirm_anyway(self):
        return self.order_id.with_context(skip_low_stock_check=True).action_confirm()
    
class LowStockWarningLine(models.TransientModel):
    _name = 'low.stock.warning.line'
    _description = 'Low Stock Warning Line'

    wizard_id = fields.Many2one('low.stock.warning.wizard', required=True, ondelete='cascade')

    product_id = fields.Many2one('product.product', readonly=True)
    stock = fields.Float(readonly=True)
    requested_qty = fields.Float(readonly=True)
    max_qty = fields.Float(readonly=True)

    stock_display = fields.Char(readonly=True)
    requested_display = fields.Char(readonly=True)
    max_display = fields.Char(readonly=True)