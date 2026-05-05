from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        extra_fields = [
            'x_is_scheduled',
            'x_schedule_level',
            'x_pos_similar_product_ids',
            'x_pos_complementary_product_ids',
            'x_has_pos_related_products',
            'qty_expired',
        ]
        for field in extra_fields:
            if field not in fields_list:
                fields_list.append(field)
        return fields_list

    def _pos_domain(self):
        domain = super()._pos_domain() if hasattr(super(), "_pos_domain") else []
        return domain + [('qty_available', '>', 0)]

    def _get_non_expired_qty(self):
        self.env.cr.execute("""
            SELECT product_id, SUM(quantity) as qty
            FROM stock_quant q
            JOIN stock_location l ON l.id = q.location_id
            WHERE l.is_expired_location = FALSE
            GROUP BY product_id
        """)
        return dict(self.env.cr.fetchall())

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        qty_map = self._get_non_expired_qty()
        filtered = []
        for product in self:
            if qty_map.get(product.id, 0) > 0:
                filtered.append(product.id)
        return {
            key: value for key, value in res.items()
            if not isinstance(value, dict) or value.get("id") in filtered
        }
