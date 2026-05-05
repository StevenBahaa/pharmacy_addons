from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_is_zero


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sell_as = fields.Selection(
        [('package', 'Package'), ('unit', 'Unit')],
        string='Sell As',
        default='package',
        required=True,
    )
    units_per_package = fields.Integer(string='Units per Package')
    package_uom_id = fields.Many2one('uom.uom', string='Package UoM', readonly=True)

    x_classification = fields.Selection(
        [('medicine', 'Medicine'), ('non_medicine', 'Non-Medicine')],
        string='Classification',
        default='non_medicine',
        required=True,
        tracking=True,
        help='Specify whether the product is a medicine or not.',
    )
    generic_name = fields.Char(
        string='Generic / Scientific Name',
        help='Scientific / INN name of the product.',
    )
    manufacturer_id = fields.Many2one(
        'res.partner',
        string='Manufacturer',
        domain="[('is_manufacturer', '=', True)]",
        help='Manufacturer linked from contacts.',
    )

    x_is_scheduled = fields.Boolean(string='Scheduled Medicine')
    x_schedule_level = fields.Selection(
        [
            ('schedule_1', 'Schedule I'),
            ('schedule_2', 'Schedule II'),
            ('schedule_3', 'Schedule III'),
            ('schedule_4', 'Schedule IV'),
            ('schedule_5', 'Schedule V'),
        ],
        string='Schedule Level',
        tracking=True,
    )

    public_price = fields.Float(
        string='Public Price',
        default=1.0,
        required=True,
        tracking=True,
    )
    gov_price_lock = fields.Boolean(string='Government Price Lock', default=False)
    currency_display_price = fields.Monetary(
        string='Price (Other Currency)',
        compute='_compute_currency_display_price',
        currency_field='currency_id',
    )
    x_avg_cost_display = fields.Char(
        string='Avg. Purchase Cost',
        compute='_compute_x_avg_cost_display',
        store=False,
    )

    similar_product_ids = fields.One2many(
        comodel_name='product.related.product',
        inverse_name='product_id',
        string='Similar / Alternative Products',
        domain=[('relation_type', '=', 'similar')],
    )
    complementary_product_ids = fields.One2many(
        comodel_name='product.related.product',
        inverse_name='product_id',
        string='Complementary Products',
        domain=[('relation_type', '=', 'complementary')],
    )

    @api.depends(
        'standard_price',
        'product_variant_ids.standard_price',
        'sell_as',
        'uom_id',
        'package_uom_id',
    )
    @api.depends_context('company')
    def _compute_x_avg_cost_display(self):
        for rec in self:
            product = rec.product_variant_id or rec.product_variant_ids[:1]
            cost_in_package = product.standard_price if product else (rec.standard_price or 0.0)
            precision_rounding = rec.currency_id.rounding if rec.currency_id else 0.01
            if not float_is_zero(cost_in_package, precision_rounding=precision_rounding):
                rec.x_avg_cost_display = f'{cost_in_package:.3f}'
            else:
                rec.x_avg_cost_display = '--'

    @api.depends('public_price')
    def _compute_currency_display_price(self):
        for rec in self:
            company = rec.env.company
            target_currency = (
                rec.env.context.get('currency_id')
                and rec.env['res.currency'].browse(rec.env.context['currency_id'])
                or company.currency_id
            )
            rec.currency_display_price = company.currency_id._convert(
                rec.public_price,
                target_currency,
                company,
                fields.Date.today(),
            )

    @api.constrains('sell_as', 'units_per_package')
    def _check_units(self):
        for rec in self:
            if rec.sell_as == 'unit' and rec.units_per_package <= 0:
                raise ValidationError(_('Units per package must be > 0'))

    @api.constrains('public_price')
    def _check_price_positive(self):
        for rec in self:
            if rec.public_price <= 0:
                raise ValidationError(_('Public price must be greater than 0'))

    @api.onchange('x_classification')
    def _onchange_x_classification(self):
        if not self.id:
            if self.x_classification == 'medicine':
                self.tracking = 'lot'
            elif self.x_classification == 'non_medicine':
                self.tracking = 'none'

    @api.onchange('sell_as', 'units_per_package')
    def _onchange_sell_as(self):
        for rec in self:
            if rec.sell_as == 'unit' and rec.units_per_package and rec.units_per_package > 0:
                package_uom = rec._get_or_create_package_uom()
                rec.uom_id = package_uom
                rec.uom_po_id = package_uom
                rec.package_uom_id = rec._create_or_get_unit_ratio_uom()
            else:
                rec.package_uom_id = False

    @api.onchange('type')
    def _onchange_force_package_uom(self):
        for rec in self:
            if not rec.id:
                package_uom = rec._get_or_create_package_uom()
                rec.uom_id = package_uom
                rec.uom_po_id = package_uom

    @api.onchange('public_price')
    def _onchange_public_price(self):
        self.list_price = self.public_price
        if self.standard_price and self.public_price < self.standard_price:
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Selling below cost. Confirm?'),
                }
            }

    @api.onchange('name')
    def _onchange_name_duplicate_warning(self):
        for rec in self:
            if not rec.name:
                continue
            domain = [('name', '=ilike', rec.name.strip())]
            if rec.id:
                domain.append(('id', '!=', rec.id))
            duplicate = self.search(domain, limit=1)
            if duplicate:
                return {
                    'warning': {
                        'title': _('Duplicate Product Name'),
                        'message': _(
                            'Another product with the name "%s" already exists.\n'
                            'Please check whether this is intentional.'
                        ) % rec.name,
                    }
                }

    @api.onchange('categ_id')
    def _onchange_categ_id_warning(self):
        if not self.categ_id:
            return {
                'warning': {
                    'title': _('Category Required'),
                    'message': _('Please select a category for this product.'),
                }
            }

    def _get_or_create_package_uom(self):
        category = self.env['uom.category'].sudo().search([
            ('name', '=', 'Package'),
        ], limit=1)
        if not category:
            category = self.env['uom.category'].sudo().create({'name': 'Package'})

        package_uom = self.env['uom.uom'].sudo().search([
            ('name', '=', 'Package'),
            ('category_id', '=', category.id),
        ], limit=1)
        if not package_uom:
            package_uom = self.env['uom.uom'].sudo().create({
                'name': 'Package',
                'category_id': category.id,
                'uom_type': 'reference',
                'factor': 1.0,
                'rounding': 0.01,
            })
        return package_uom

    def _create_or_get_unit_ratio_uom(self):
        self.ensure_one()
        if not self.units_per_package or self.units_per_package <= 0:
            raise ValidationError(_('Units per package must be greater than zero.'))

        package_uom = self._get_or_create_package_uom()
        name = f'1 unit of {int(self.units_per_package)} units per Package'
        uom = self.env['uom.uom'].sudo().search([
            ('name', '=', name),
            ('category_id', '=', package_uom.category_id.id),
        ], limit=1)
        if not uom:
            uom = self.env['uom.uom'].sudo().create({
                'name': name,
                'category_id': package_uom.category_id.id,
                'uom_type': 'smaller',
                'factor': self.units_per_package,
                'rounding': 0.01,
            })
        return uom

    def _check_gov_price_lock_access(self, vals):
        if 'gov_price_lock' not in vals:
            return
        for rec in self:
            if vals['gov_price_lock'] != rec.gov_price_lock:
                if not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
                    raise ValidationError(_(
                        'Only a Pharmacy Manager can change Government Price Lock.'
                    ))

    def _check_public_price_change_allowed(self, vals):
        if 'public_price' not in vals:
            return
        for rec in self:
            if rec.gov_price_lock:
                raise UserError(_('Price is government-regulated and cannot be changed.'))

    def _check_tracking_change_allowed(self, vals):
        if 'tracking' not in vals:
            return
        for rec in self:
            has_stock_moves = self.env['stock.move'].search_count([
                ('product_id', 'in', rec.product_variant_ids.ids),
                ('state', '!=', 'cancel'),
            ], limit=1)
            if has_stock_moves and rec.tracking != vals['tracking']:
                tracking_selection = dict(rec._fields['tracking'].selection)
                current_label = tracking_selection.get(rec.tracking, rec.tracking)
                new_label = tracking_selection.get(vals['tracking'], vals['tracking'])
                raise UserError(_(
                    'Cannot change tracking method for product "%(name)s" '
                    'because it already has stock transactions.\n'
                    'Current tracking: %(current)s\n'
                    'Attempted change to: %(new)s'
                ) % {
                    'name': rec.name,
                    'current': current_label,
                    'new': new_label,
                })

    def _sync_package_uom_after_write(self):
        for rec in self:
            if rec.sell_as == 'unit' and rec.units_per_package:
                uom = rec._create_or_get_unit_ratio_uom()
                if rec.package_uom_id != uom:
                    super(ProductTemplate, rec).write({'package_uom_id': uom.id})

    @api.model_create_multi
    def create(self, vals_list):
        package_uom = self._get_or_create_package_uom()
        for vals in vals_list:
            vals['uom_id'] = package_uom.id
            vals['uom_po_id'] = package_uom.id
            if not vals.get('public_price'):
                vals['public_price'] = vals.get('list_price') or 1.0
            if vals.get('gov_price_lock'):
                if not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
                    raise ValidationError(_(
                        'Only a Pharmacy Manager can enable Government Price Lock.'
                    ))

        records = super().create(vals_list)
        for rec in records:
            if rec.sell_as == 'unit' and rec.units_per_package:
                uom = rec._create_or_get_unit_ratio_uom()
                super(ProductTemplate, rec).write({'package_uom_id': uom.id})
        return records

    def write(self, vals):
        vals = dict(vals)
        self._check_gov_price_lock_access(vals)
        self._check_public_price_change_allowed(vals)
        self._check_tracking_change_allowed(vals)
        res = super().write(vals)
        self._sync_package_uom_after_write()
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('generic_name', operator, name)],
            ])
            args = expression.AND([args, domain])
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
