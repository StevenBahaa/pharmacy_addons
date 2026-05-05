from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # -------------------------------------------------------------------------
    # FIELDS: UOM LOCKING
    # -------------------------------------------------------------------------
    purchase_uom_readonly = fields.Boolean(
        string='Purchase UoM Readonly',
        compute='_compute_purchase_uom_readonly',
        help='Technical field to indicate UoM cannot be changed',
    )

    # -------------------------------------------------------------------------
    # COMPUTE: UOM LOCKING
    # -------------------------------------------------------------------------
    @api.depends('product_id')
    def _compute_purchase_uom_readonly(self):
        """Always readonly when product is set"""
        for line in self:
            line.purchase_uom_readonly = bool(line.product_id)

    # -------------------------------------------------------------------------
    # HELPERS: PACKAGE UOM
    # -------------------------------------------------------------------------
    def _get_expected_purchase_package_uom(self):
        self.ensure_one()

        if not self.product_id:
            return False

        # In pharmacy logic, native product UoM is the package UoM.
        return self.product_id.uom_id

    # -------------------------------------------------------------------------
    # ONCHANGE: FORCE PACKAGE UOM
    # -------------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id_force_package_uom(self):
        for line in self:
            expected_uom = line._get_expected_purchase_package_uom()
            if expected_uom:
                line.product_uom = expected_uom

    @api.onchange('product_uom', 'product_id')
    def _onchange_product_uom_keep_package(self):
        """
        Client-side safety: if any UI path tries to change UoM,
        force it back to the product package (native UoM).
        """
        for line in self:
            expected_uom = line._get_expected_purchase_package_uom()
            if expected_uom and line.product_uom and line.product_uom != expected_uom:
                line.product_uom = expected_uom

    # -------------------------------------------------------------------------
    # CONSTRAINTS: PREVENT NON-PACKAGE PURCHASE UOM
    # -------------------------------------------------------------------------
    @api.constrains('product_id', 'product_uom')
    def _check_purchase_uom_is_package(self):
        for line in self:
            if not line.product_id or not line.product_uom:
                continue

            expected_uom = line._get_expected_purchase_package_uom()

            if expected_uom and line.product_uom != expected_uom:
                raise ValidationError(
                    _(
                        'You cannot change the purchase UoM for "%(product)s".\n'
                        'Purchases must be done using the package UoM: %(uom)s.'
                    ) % {
                        'product': line.product_id.display_name,
                        'uom': expected_uom.display_name,
                    }
                )

    # -------------------------------------------------------------------------
    # ORM OVERRIDES: CREATE
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Product = self.env['product.product']

        for vals in vals_list:
            if vals.get('product_id'):
                product = Product.browse(vals['product_id'])
                expected_uom = product.uom_id
                if expected_uom:
                    vals['product_uom'] = expected_uom.id

        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # ORM OVERRIDES: WRITE
    # -------------------------------------------------------------------------
    def write(self, vals):
        vals = dict(vals)

        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            expected_uom = product.uom_id
            if expected_uom:
                vals['product_uom'] = expected_uom.id

        elif 'product_uom' in vals:
            for line in self:
                expected_uom = line._get_expected_purchase_package_uom()
                if expected_uom and vals['product_uom'] != expected_uom.id:
                    raise ValidationError(
                        _(
                            'You cannot change the purchase UoM for "%(product)s".\n'
                            'Purchases must be done using the package UoM: %(uom)s.'
                        ) % {
                            'product': line.product_id.display_name,
                            'uom': expected_uom.display_name,
                        }
                    )

        return super().write(vals)