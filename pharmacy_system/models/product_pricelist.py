from odoo import fields, models
from odoo.exceptions import ValidationError

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _get_product_price(self, product, quantity=1.0, partner=False, date=False, uom_id=False):
        # 🚫 Block pricelist if government locked
        if product.gov_price_lock:
            raise ValidationError(
                "Cannot apply pricelist on government-regulated product."
            )

        # Continue normal behavior
        return super()._get_product_price(product, quantity, partner, date, uom_id)
    
class ProductPriceHistory(models.Model):
    _name = 'product.price.history'
    _description = 'Price History'

    product_id = fields.Many2one('product.template')
    date = fields.Datetime(default=fields.Datetime.now)
    old_price = fields.Float()
    new_price = fields.Float()
    changed_by = fields.Many2one('res.users')