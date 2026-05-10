from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # الدالة اللي الزرار بيدور عليها
    def action_create_purchase_order(self):
        self.ensure_one()
        # حسبة الكمية المطلوبة بناءً على معايير القبول (الاحتياج - الموجود)
        qty_to_order = self.forecast_need_3m - self.qty_available
        
        if qty_to_order <= 0:
            return
            
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'context': {
                # بيختار أول مورد مربوط بالدواء تلقائياً
                'default_partner_id': self.seller_ids[0].partner_id.id if self.seller_ids else False,
                'default_order_line': [(0, 0, {
                    'product_id': self.id,
                    'product_qty': qty_to_order,
                    'price_unit': self.standard_price,
                })],
            },
        }