from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrderSuggestedProductsWizard(models.TransientModel):
    _name = 'sale.order.suggested.products.wizard'
    _description = 'Sale Order Suggested Products Wizard'

    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        required=True,
        readonly=True,
    )

    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sale Order Line',
        required=True,
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Current Product',
        readonly=True,
    )

    suggestion_line_ids = fields.One2many(
        comodel_name='sale.order.suggested.products.wizard.line',
        inverse_name='wizard_id',
        string='Suggested Products',
    )


class SaleOrderSuggestedProductsWizardLine(models.TransientModel):
    _name = 'sale.order.suggested.products.wizard.line'
    _description = 'Sale Order Suggested Products Wizard Line'
    _order = 'relation_type, priority desc, id'


    wizard_id = fields.Many2one(
        comodel_name='sale.order.suggested.products.wizard',
        required=True,
        ondelete='cascade',
    )

    relation_type = fields.Selection(
        selection=[
            ('similar', 'Similar / Alternative'),
            ('complementary', 'Complementary'),
        ],
        string='Type',
        readonly=True,
    )

    related_product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Suggested Product',
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product Variant',
        compute='_compute_product_id',
        store=False,
    )

    priority = fields.Integer(
        string='Priority',
        readonly=True,
    )

    note = fields.Text(
        string='Note',
        readonly=True,
    )

    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_product_info'
    )

    sales_price = fields.Float(
        string='Sales Price',
        compute='_compute_product_info'
    )

    categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Category',
        compute='_compute_product_info'
    )

    @api.depends('product_id')
    def _compute_product_info(self):
        for line in self:
            product = line.product_id

            line.available_qty = product.qty_available if product else 0.0
            line.sales_price = product.lst_price if product else 0.0
            line.categ_id = product.categ_id if product else False


    @api.depends('related_product_tmpl_id')
    def _compute_product_id(self):
        for line in self:
            line.product_id = line.related_product_tmpl_id.product_variant_id if line.related_product_tmpl_id else False

    def action_add_to_order(self):
        for line in self:
            wizard = line.wizard_id

            if not line.product_id:
                raise UserError(_('No product variant found for this suggested product.'))

            wizard.sale_order_id.order_line.create({
                'order_id': wizard.sale_order_id.id,
                'product_id': line.product_id.id,
                'product_uom_qty': 1,
            })

        return {'type': 'ir.actions.act_window_close'}

    def action_replace_current_product(self):
        for line in self:
            wizard = line.wizard_id

            if not line.product_id:
                raise UserError(_('No product variant found for this suggested product.'))

            wizard.sale_order_line_id.product_id = line.product_id.id
            wizard.sale_order_line_id.product_uom_qty = wizard.sale_order_line_id.product_uom_qty or 1

        return {'type': 'ir.actions.act_window_close'}