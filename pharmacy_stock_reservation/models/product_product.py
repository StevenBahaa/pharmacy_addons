from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'
    # Displayed as "On Hand: 100 | Reserved: 30 | Available: 70"
    pharmacy_reserved_qty = fields.Float(
        string='Reserved Qty',
        digits='Product Unit of Measure',
        compute='_compute_pharmacy_stock_summary',
        help='Total units committed to confirmed transfers across all internal locations.',
    )
    pharmacy_available_qty = fields.Float(
        string='Available Qty',
        digits='Product Unit of Measure',
        compute='_compute_pharmacy_stock_summary',
        help='On Hand minus Reserved.',
    )
    @api.depends('stock_quant_ids.quantity', 'stock_quant_ids.pharmacy_reserved_qty')
    def _compute_pharmacy_stock_summary(self):
        for product in self:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
            ])
            product.pharmacy_reserved_qty = sum(quants.mapped('pharmacy_reserved_qty'))
            total_onhand = sum(quants.mapped('quantity'))
            product.pharmacy_available_qty = total_onhand - product.pharmacy_reserved_qty
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    pharmacy_reserved_qty = fields.Float(
        string='Reserved Qty',
        digits='Product Unit of Measure',
        compute='_compute_pharmacy_stock_summary',
    )
    pharmacy_available_qty = fields.Float(
        string='Available Qty',
        digits='Product Unit of Measure',
        compute='_compute_pharmacy_stock_summary',
    )
    @api.depends('product_variant_ids.pharmacy_reserved_qty',
                 'product_variant_ids.pharmacy_available_qty')
    def _compute_pharmacy_stock_summary(self):
        for tmpl in self:
            tmpl.pharmacy_reserved_qty = sum(
                tmpl.product_variant_ids.mapped('pharmacy_reserved_qty')
            )
            tmpl.pharmacy_available_qty = sum(
                tmpl.product_variant_ids.mapped('pharmacy_available_qty')
            )