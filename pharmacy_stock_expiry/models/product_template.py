from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_expired = fields.Float(
        string="Expired Qty",
        compute="_compute_expired_qty",
    )

    def _compute_expired_qty(self):
        for template in self:
            template.qty_expired = sum(
                template.product_variant_ids.mapped('qty_expired')
            )

    def action_open_expired_stock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Stock',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id.product_tmpl_id', '=', self.id),
                ('location_id.is_expired_location', '=', True),
            ],
        }
