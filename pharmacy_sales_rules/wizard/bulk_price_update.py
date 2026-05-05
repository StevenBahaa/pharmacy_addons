from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BulkPriceUpdateWizard(models.TransientModel):
    _name = 'bulk.price.update'
    _description = 'Bulk Price Update Wizard'

    product_ids = fields.Many2many('product.template', string="Products")

    update_type = fields.Selection([
        ('percent_increase', 'Percentage Increase'),
        ('percent_decrease', 'Percentage Decrease'),
        ('fixed_increase', 'Fixed Increase'),
        ('fixed_decrease', 'Fixed Decrease'),
    ], required=True)

    value = fields.Float(required=True)



    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')

        if active_ids:
            res['product_ids'] = [(6, 0, active_ids)]

        return res

    def action_apply(self):
        for product in self.product_ids:
            if product.gov_price_lock:
                continue

            old_price = product.public_price

            if self.update_type == 'percent_increase':
                new_price = old_price + (old_price * self.value / 100)

            elif self.update_type == 'percent_decrease':
                new_price = old_price - (old_price * self.value / 100)

            elif self.update_type == 'fixed_increase':
                new_price = old_price + self.value

            elif self.update_type == 'fixed_decrease':
                new_price = old_price - self.value

            if new_price <= 0:
                raise ValidationError("Public price cannot be zero or negative")

            product.write({
                'public_price': new_price
            })

        return {'type': 'ir.actions.act_window_close'}