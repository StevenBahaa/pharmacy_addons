from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        # Always allow these custom fields as they are needed for pharmacy logic
        extra_fields = [
            'x_is_scheduled',
            'x_schedule_level',
            'x_pos_similar_product_ids',
            'x_pos_complementary_product_ids',
            'x_has_pos_related_products',
            'qty_expired',
            'qty_available',
        ]
        for field in extra_fields:
            if field not in fields_list:
                fields_list.append(field)

        # Security: Remove standard_price (cost) if user is not authorized
        if not self.env.user.has_group('pharmacy_base.group_pricing_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            if 'standard_price' in fields_list:
                fields_list.remove('standard_price')

        return fields_list

    def _load_pos_data(self, data):
        """Ensure all pharmacy-relevant products load, including those with 0 stock
        so the Wishlist feature can function.
        Also performs a second pass to zero out sensitive values if they leaked.
        """
        res = super()._load_pos_data(data)
        if not self.env.user.has_group('pharmacy_base.group_pricing_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            for product in res.get('data', []):
                if 'standard_price' in product:
                    product['standard_price'] = 0.0
        return res

    def _pos_domain(self):
        """Allow out-of-stock products to load so they can be added to the Wishlist."""      
        return super()._pos_domain() if hasattr(super(), "_pos_domain") else []

    def _get_non_expired_qty(self):
        self.env.cr.execute("""
            SELECT product_id, SUM(quantity) as qty
            FROM stock_quant q
            JOIN stock_location l ON l.id = q.location_id
            WHERE l.is_expired_location = FALSE
            GROUP BY product_id
        """)
        return dict(self.env.cr.fetchall())
