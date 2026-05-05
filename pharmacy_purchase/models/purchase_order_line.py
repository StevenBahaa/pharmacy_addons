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
    # HELPERS: Consignment Receipt
    # -------------------------------------------------------------------------
    def _get_consignment_receipt_start_date(self):
        self.ensure_one()
        pickings = self.order_id.picking_ids.filtered(
            lambda p: p.state == "done" and p.picking_type_id.code == "incoming"
        )

        if not pickings:
            return False
        
        return min(pickings.mapped("date_done"))

    def _get_consignment_sold_qty_sales_only(self):
        self.ensure_one()
        start_date = self._get_consignment_receipt_start_date()

        if not start_date:
            return 0.0

        # Get the destination locations from the PO pickings
        pickings = self.order_id.picking_ids.filtered(
            lambda p: p.state == "done" and p.picking_type_id.code == "incoming"
        )
        location_ids = pickings.mapped("location_dest_id").ids

        domain = [
            ('product_id', '=', self.product_id.id),
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', start_date),
            '|',
            ('product_id.seller_ids.partner_id', '=', self.order_id.partner_id.id),
            ('product_id.manufacturer_id', '=', self.order_id.partner_id.id),
        ]

        
        # If we have specific locations, we should ideally filter sales by warehouse/location.
        # In standard Odoo, sale.order.line doesn't have a direct location_id, but the order has a warehouse_id.
        # However, stock.move has location_id. Let's use stock.move instead for more accuracy if needed,
        # or just warehouse_id from the sale order.
        # The prompt says "filtered by location".
        
        # 1. Search Sale Order Lines
        sale_lines = self.env['sale.order.line'].search(domain)
        
        # 2. Search POS Order Lines (using same start date and product)
        pos_domain = [
            ('product_id', '=', self.product_id.id),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('order_id.date_order', '>=', start_date),
            '|',
            ('product_id.seller_ids.partner_id', '=', self.order_id.partner_id.id),
            ('product_id.manufacturer_id', '=', self.order_id.partner_id.id),
        ]
        pos_lines = self.env['pos.order.line'].search(pos_domain)

        # Filter lines by warehouse if the PO pickings are in a specific warehouse
        if location_ids:
            warehouses = self.env['stock.warehouse'].search([('lot_stock_id', 'in', location_ids)])
            if warehouses:
                sale_lines = sale_lines.filtered(lambda l: l.order_id.warehouse_id in warehouses)
                # POS orders are linked to a warehouse via the POS session's config
                pos_lines = pos_lines.filtered(lambda l: l.order_id.config_id.warehouse_id in warehouses)

        sold_qty = 0.0
        # Sum from Sale Orders
        for sale_line in sale_lines:
            sold_qty += sale_line.product_uom._compute_quantity(
                sale_line.product_uom_qty,
                self.product_uom,
            )
        
        # Sum from POS Orders
        for pos_line in pos_lines:
            sold_qty += pos_line.product_uom._compute_quantity(
                pos_line.qty,
                self.product_uom,
            )

        return sold_qty



    def _get_consignment_already_paid_qty(self):
        self.ensure_one()

        payments = self.env["pharmacy.consignment.payment"].search([
            ('purchase_order_line_id', '=', self.id),
            ("vendor_bill_id.state", "!=", "cancel"),
        ])

        return sum(payments.mapped('quantity_paid'))

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

    