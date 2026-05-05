from odoo import api, fields, models, _


class SaleCommissionEntry(models.Model):
    _name = 'sale.commission.entry'
    _description = 'Sales Commission Entry'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')

    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now)

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
    )

    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Sales Order Line',
        required=True,
        ondelete='cascade',
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery/Return',
        ondelete='set null',
    )

    stock_move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        ondelete='set null',
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        required=True,
        index=True,
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        index=True,
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
    )

    entry_type = fields.Selection(
        [
            ('delivery', 'Delivery'),
            ('return', 'Return'),
        ],
        string='Entry Type',
        required=True,
        index=True,
    )

    quantity = fields.Float(string='Quantity', required=True)
    unit_sale_price = fields.Float(string='Unit Sale Price', required=True)
    unit_cost = fields.Float(string='Unit Cost', required=True)
    unit_margin = fields.Float(string='Unit Margin', required=True)
    commission_percentage = fields.Float(string='Commission %', required=True)

    margin_base = fields.Monetary(
        string='Margin Base',
        currency_field='currency_id',
        required=True,
    )

    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        required=True,
    )

    note = fields.Char(string='Note')


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.commission.entry') or 'New'
        return super().create(vals_list)