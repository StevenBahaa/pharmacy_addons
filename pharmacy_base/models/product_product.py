from odoo import api, fields, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = 'product.product'

    x_is_scheduled = fields.Boolean(
        related='product_tmpl_id.x_is_scheduled',
        store=True,
        readonly=True,
    )
    x_schedule_level = fields.Selection(
        related='product_tmpl_id.x_schedule_level',
        store=True,
        readonly=True,
    )
    x_pos_similar_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='POS Similar Products',
        compute='_compute_pos_related_products',
    )
    x_pos_complementary_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='POS Complementary Products',
        compute='_compute_pos_related_products',
    )
    x_has_pos_related_products = fields.Boolean(
        string='Has POS Related Products',
        compute='_compute_pos_related_products',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                vals['default_code'] = self.env['ir.sequence'].next_by_code(
                    'product.internal.reference'
                ) or '/'
        return super().create(vals_list)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('product_tmpl_id.generic_name', operator, name)],
            ])
            domain = expression.AND([domain, name_domain])
        return self._search(domain, limit=limit, order=order)

    @api.depends(
        'product_tmpl_id.similar_product_ids',
        'product_tmpl_id.complementary_product_ids',
        'product_tmpl_id.similar_product_ids.related_product_id',
        'product_tmpl_id.complementary_product_ids.related_product_id',
        'product_tmpl_id.similar_product_ids.active',
        'product_tmpl_id.complementary_product_ids.active',
        'product_tmpl_id.similar_product_ids.priority',
        'product_tmpl_id.complementary_product_ids.priority',
    )
    def _compute_pos_related_products(self):
        for product in self:
            similar_variants = self.env['product.product']
            complementary_variants = self.env['product.product']
            
            if product.product_tmpl_id:
                related_records = self.env['product.related.product'].sudo().search([
                    ('product_id', '=', product.product_tmpl_id.id),
                    ('active', '=', True)
                ])
                
                similar_variants = related_records.filtered(
                    lambda r: r.relation_type == 'similar'
                ).mapped('related_product_id.product_variant_id')
                
                complementary_variants = related_records.filtered(
                    lambda r: r.relation_type == 'complementary'
                ).mapped('related_product_id.product_variant_id')

            product.x_pos_similar_product_ids = similar_variants
            product.x_pos_complementary_product_ids = complementary_variants
            product.x_has_pos_related_products = bool(similar_variants or complementary_variants)
