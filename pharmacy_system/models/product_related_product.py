from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError


class RelatedProduct(models.Model):
    _name = 'product.related.product'
    _description = 'Product Related Product'
    _order = 'priority, related_product_id'

    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='cascade'
    )

    related_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Related Product',
        required=True,
        ondelete='cascade'
    )

    relation_type = fields.Selection(
        selection=[
            ('similar', 'Similar / Alternative'),
            ('complementary', 'Complementary'),
        ],
        string='Relation Type',
        required=True,
    )

    note = fields.Text(
        string='Internal Note'
    )

    priority = fields.Selection(
        selection=[
            ('1', '1 - Low'),
            ('2', '2'),
            ('3', '3 - Medium'),
            ('4', '4'),
            ('5', '5 - High'),
        ],
        string='Priority',
        default='5',
        required=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    _sql_constraints = [
        (
            'unique_product_related_type',
            'unique(product_id, related_product_id, relation_type)',
            'This related product is already added for this relation type.'
        ),
    ]

    @api.constrains('product_id', 'related_product_id')
    def _check_product_not_related_to_itself(self):
        for rec in self:
            if rec.product_id and rec.related_product_id and rec.product_id == rec.related_product_id:
                raise ValidationError(_('A product cannot be related to itself.'))
            
    def action_make_reciprocal(self):
        for rec in self :
            if not rec.product_id or not rec.related_product_id:
                continue

            existing_relation = self.search([
                ('product_id' , '=' , rec.related_product_id.id),
                ('related_product_id' , '=' , rec.product_id.id ),
                ('relation_type' , '=' , rec.relation_type),  
            ], limit=1)

            if existing_relation:
                raise UserError(_('The reciprocal relation already exists.'))
            
            self.create({
                'product_id' : rec.related_product_id.id, 
                'related_product_id': rec.product_id.id,
                'relation_type': rec.relation_type, 
                'priority':rec.priority,
                'note':rec.note,
                'active':rec.active,
            })


    # @api.constrains('priority')
    # def _check_priority(self):
    #     for rec in self:
    #         if rec.priority < 1 or rec.priority > 5:
    #             raise ValidationError(_('The Priority must be between 1 and 5.'))