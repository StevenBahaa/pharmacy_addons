from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_expired = fields.Float(
        string="Expired Qty",
        compute="_compute_expired_qty",
    )

    def _compute_expired_qty(self):
        for product in self:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.is_expired_location', '=', True),
            ])
            product.qty_expired = sum(quants.mapped('quantity'))

    def action_open_expired_stock_variant(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Stock',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id', '=', self.id),
                ('location_id.is_expired_location', '=', True),
            ],
            'context': {
                'search_default_expired_stock': 1,
            },
        }

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super()._compute_quantities_dict(
            lot_id,
            owner_id,
            package_id,
            from_date,
            to_date,
        )

        for product in self:
            expired_quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.is_expired_location', '=', True),
            ])
            expired_qty = sum(expired_quants.mapped('quantity'))

            res[product.id]['qty_available'] -= expired_qty
            res[product.id]['virtual_available'] -= expired_qty

        return res
