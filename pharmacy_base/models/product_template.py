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

    x_is_scheduled = fields.Boolean(
        string='Scheduled Medicine',
    )
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
    gov_price_lock = fields.Boolean(
        string='Government Price Lock',
        default=False,
    )
    standard_price = fields.Float(groups="pharmacy_base.group_pricing_manager,pharmacy_base.group_pharmacy_manager")
    currency_display_price = fields.Monetary(
        string='Price (Other Currency)',
        compute='_compute_currency_display_price',
        currency_field='currency_id',
    )
    x_avg_cost_display = fields.Char(
        string='Avg. Purchase Cost',
        compute='_compute_x_avg_cost_display',
        store=False,
        groups="pharmacy_base.group_pricing_manager,pharmacy_base.group_pharmacy_manager",
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
        # Use sudo to allow internal recomputation for all users to prevent AccessErrors 
        # when non-restricted fields change. Field visibility is handled by groups attribute.
        for rec in self.sudo():
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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        package_uom = self._get_or_create_package_uom()
        if 'uom_id' in fields_list:
            res['uom_id'] = package_uom.id
        if 'uom_po_id' in fields_list:
            res['uom_po_id'] = package_uom.id
        return res

    @api.onchange('sell_as', 'units_per_package')
    def _onchange_sell_as(self):
        for rec in self:
            package_uom = rec._get_or_create_package_uom()
            if rec.sell_as == 'unit' and rec.units_per_package and rec.units_per_package > 0:
                rec.uom_id = package_uom.id
                rec.uom_po_id = package_uom.id
                rec.package_uom_id = rec._create_or_get_unit_ratio_uom().id
            else:
                rec.uom_id = package_uom.id
                rec.uom_po_id = package_uom.id
                rec.package_uom_id = False

    @api.onchange('type')
    def _onchange_force_package_uom(self):
        for rec in self:
            if not rec.id:
                package_uom = rec._get_or_create_package_uom()
                rec.uom_id = package_uom.id
                rec.uom_po_id = package_uom.id

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
        # 1. Try by XML ID first (most reliable)
        package_uom = self.env.ref('pharmacy_base.uom_uom_package', raise_if_not_found=False)
        if package_uom:
            return package_uom.sudo()

        # 2. Fallback to name search
        category = self.env['uom.category'].sudo().search([('name', '=', 'Package')], limit=1)
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
        return package_uom.sudo()

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

    def _create_audit_log(self, action_type, old_value, new_value, note=None):
        self.ensure_one()
        self.env['pharmacy.audit.log'].sudo().create({
            'user_id': self.env.user.id,
            'model_name': self._name,
            'res_id': self.id,
            'action_type': action_type,
            'old_value': str(old_value),
            'new_value': str(new_value),
            'note': note,
        })

    def _check_category_change_allowed(self, vals):
        if 'categ_id' not in vals:
            return
        if not self.env.user.has_group('pharmacy_base.group_product_config_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_('You are not authorized to change product categories.'))

    def _log_security_changes(self, vals):
        for rec in self:
            if 'x_classification' in vals and vals['x_classification'] != rec.x_classification:
                rec._create_audit_log('classification_change', rec.x_classification, vals['x_classification'])
            if 'gov_price_lock' in vals and vals['gov_price_lock'] != rec.gov_price_lock:
                rec._create_audit_log('price_override', f"Lock: {rec.gov_price_lock}", f"Lock: {vals['gov_price_lock']}")
            if 'x_schedule_level' in vals and vals['x_schedule_level'] != rec.x_schedule_level:
                rec._create_audit_log('scheduled_medicine_change', rec.x_schedule_level, vals['x_schedule_level'])
            if 'x_is_scheduled' in vals and vals['x_is_scheduled'] != rec.x_is_scheduled:
                rec._create_audit_log('scheduled_medicine_change', f"Scheduled: {rec.x_is_scheduled}", f"Scheduled: {vals['x_is_scheduled']}")

    @api.model_create_multi
    def create(self, vals_list):
        package_uom = self._get_or_create_package_uom()
        for vals in vals_list:
            # Force same category for both UoMs to prevent Odoo constraint error
            vals['uom_id'] = package_uom.id
            vals['uom_po_id'] = package_uom.id
        records = super().create(vals_list)
        records._sync_package_uom_after_write()
        return records

    def write(self, vals):
        vals = dict(vals)

        # Force UoM consistency — always same Package category
        package_uom = self._get_or_create_package_uom()
        if 'uom_id' in vals or 'uom_po_id' in vals:
            vals['uom_id'] = package_uom.id
            vals['uom_po_id'] = package_uom.id

        res = super().write(vals)
        self._sync_package_uom_after_write()
        return res

    def _sync_package_uom_after_write(self):
        package_uom = self._get_or_create_package_uom()
        for rec in self:
            if rec.sell_as == 'package':
                if rec.uom_id != package_uom or rec.uom_po_id != package_uom or rec.package_uom_id:
                    super(ProductTemplate, rec).write({
                        'uom_id': package_uom.id,
                        'uom_po_id': package_uom.id,
                        'package_uom_id': False,
                    })
            elif rec.sell_as == 'unit' and rec.units_per_package:
                uom = rec._create_or_get_unit_ratio_uom()
                if rec.package_uom_id != uom or rec.uom_id != package_uom or rec.uom_po_id != package_uom:
                    super(ProductTemplate, rec).write({
                        'uom_id': package_uom.id,
                        'uom_po_id': package_uom.id,
                        'package_uom_id': uom.id,
                    })

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('generic_name', operator, name)],
            ])
            domain = expression.AND([domain, name_domain])
        return self._search(domain, limit=limit, order=order)