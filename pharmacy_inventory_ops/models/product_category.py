from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.onchange('property_cost_method')
    def _onchange_force_avco(self):
        self.property_cost_method = 'average'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['property_cost_method'] = 'average'
        records = super().create(vals_list)
        # Update ALL ir.default records for property_cost_method to 'average'
        field = self.env['ir.model.fields']._get('product.category', 'property_cost_method')
        defaults = self.env['ir.default'].sudo().search([('field_id', '=', field.id)])
        if defaults:
            defaults.write({'json_value': '"average"'})
        else:
            self.env['ir.default'].sudo().create({
                'field_id': field.id,
                'json_value': '"average"',
            })
        return records