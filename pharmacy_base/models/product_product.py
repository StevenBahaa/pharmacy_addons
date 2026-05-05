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
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('product_tmpl_id.generic_name', operator, name)],
            ])
            args = expression.AND([args, domain])
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

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
            similar_lines = product.product_tmpl_id.similar_product_ids.filtered(
                lambda line: line.active and line.related_product_id
            ).sorted(lambda line: line.priority, reverse=True)
            complementary_lines = product.product_tmpl_id.complementary_product_ids.filtered(
                lambda line: line.active and line.related_product_id
            ).sorted(lambda line: line.priority, reverse=True)

            similar_products = similar_lines.mapped('related_product_id.product_variant_id')
            complementary_products = complementary_lines.mapped('related_product_id.product_variant_id')

            product.x_pos_similar_product_ids = similar_products
            product.x_pos_complementary_product_ids = complementary_products
            product.x_has_pos_related_products = bool(similar_products or complementary_products)
