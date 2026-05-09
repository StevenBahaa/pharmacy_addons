from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PeriodicCountWizard(models.TransientModel):
    """
    Wizard to initiate a Periodic Full Count session.
    Lets the manager select warehouse, optional category, optional location,
    then generates pharmacy.count with pre-filled lines from current stock.
    """
    _name = 'pharmacy.count.wizard'
    _description = 'New Periodic Count Wizard'

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        ),
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Specific Location',
        domain="[('usage', '=', 'internal')]",
        help='Leave blank to count all internal locations of the warehouse.',
    )
    category_id = fields.Many2one(
        comodel_name='product.category',
        string='Product Category',
        help='Leave blank to count all categories.',
    )
    count_date = fields.Date(
        string='Count Date',
        required=True,
        default=fields.Date.today,
    )
    responsible_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        required=True,
    )

    # ------------------------------------------------------------------ #
    def action_create_count(self):
        self.ensure_one()
        warehouse = self.warehouse_id

        # --- Determine locations to include ---
        if self.location_id:
            locations = self.location_id
        else:
            locations = self.env['stock.location'].search([
                ('location_id', 'child_of', warehouse.view_location_id.id),
                ('usage', '=', 'internal'),
                ('active', '=', True),
            ])

        if not locations:
            raise UserError(_('No internal locations found for the selected warehouse.'))

        # --- Build product domain ---
        product_domain = [
            ('type', 'in', ['product', 'consu']),
            ('active', '=', True),
        ]
        if self.category_id:
            # Include subcategories
            cat_ids = self.env['product.category'].search([
                ('id', 'child_of', self.category_id.id)
            ]).ids
            product_domain.append(('categ_id', 'in', cat_ids))

        # --- Fetch quants for those locations ---
        quant_domain = [('location_id', 'in', locations.ids)]
        if self.category_id:
            cat_ids = self.env['product.category'].search([
                ('id', 'child_of', self.category_id.id)
            ]).ids
            quant_domain.append(('product_id.categ_id', 'in', cat_ids))

        quants = self.env['stock.quant'].search(quant_domain)

        # Also add storable products with zero qty (not in quants) if category filter
        products_with_quant = quants.mapped('product_id')
        extra_products = self.env['product.product'].search(
            product_domain + [('id', 'not in', products_with_quant.ids)]
        )

        # --- Create the count header ---
        count = self.env['pharmacy.count'].create({
            'count_type': 'periodic',
            'count_date': self.count_date,
            'warehouse_id': warehouse.id,
            'location_id': self.location_id.id if self.location_id else False,
            'category_id': self.category_id.id if self.category_id else False,
            'responsible_id': self.responsible_id.id,
            'state': 'in_progress',
        })

        # --- Build lines from quants ---
        line_vals = []
        seen = set()  # (product_id, location_id)

        for quant in quants:
            key = (quant.product_id.id, quant.location_id.id)
            if key in seen:
                continue
            seen.add(key)
            line_vals.append({
                'count_id': count.id,
                'product_id': quant.product_id.id,
                'location_id': quant.location_id.id,
                'expected_qty': quant.quantity,
                'counted_status': 'not_started',
            })

        # Lines for products with zero on-hand
        default_location = self.location_id or warehouse.lot_stock_id
        for product in extra_products:
            key = (product.id, default_location.id)
            if key in seen:
                continue
            seen.add(key)
            line_vals.append({
                'count_id': count.id,
                'product_id': product.id,
                'location_id': default_location.id,
                'expected_qty': 0.0,
                'counted_status': 'not_started',
            })

        if not line_vals:
            count.unlink()
            raise UserError(
                _('No products found for the selected criteria. '
                  'Please adjust the filters.')
            )

        self.env['pharmacy.count.line'].create(line_vals)

        # --- Open the created count ---
        return {
            'type': 'ir.actions.act_window',
            'name': _('Periodic Count'),
            'res_model': 'pharmacy.count',
            'res_id': count.id,
            'view_mode': 'form',
            'target': 'current',
        }
