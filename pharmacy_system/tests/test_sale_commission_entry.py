from odoo.tests.common import TransactionCase
from odoo import fields


class TestSaleCommissionEntry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.company.enable_product_commission = True

        cls.customer = cls.env['res.partner'].create({
            'name': 'Commission Test Customer',
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Commission Test Product',
            'type': 'consu',
            'list_price': 100.0,
            'standard_price': 60.0,
            'commission_percentage': 10.0,   # if field is on product.product
        })

        # If your commission field is on product.template instead, use this:
        cls.product.product_tmpl_id.commission_percentage = 10.0

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'company_id': cls.company.id,
            'date_order': fields.Datetime.now(),
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 5.0,
                'price_unit': 100.0,
            })]
        })

        cls.sale_order.action_confirm()
        cls.sale_line = cls.sale_order.order_line[:1]

    def _validate_delivery(self, sale_order, qty_done=5.0):
        picking = sale_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))[:1]
        self.assertTrue(picking, "No delivery picking found.")

        for move in picking.move_ids:
            move.quantity = qty_done

        picking.action_confirm()
        picking.action_assign()

        for move_line in picking.move_line_ids:
            move_line.quantity = qty_done

        picking.button_validate()
        return picking

    def test_commission_entry_created_on_delivery(self):
        self._validate_delivery(self.sale_order, qty_done=5.0)

        entries = self.env['sale.commission.entry'].search([
            ('sale_order_line_id', '=', self.sale_line.id)
        ])

        self.assertEqual(len(entries), 1, "A commission entry should be created on delivery.")

        entry = entries[0]
        self.assertEqual(entry.entry_type, 'delivery')
        self.assertEqual(entry.quantity, 5.0)
        self.assertEqual(entry.salesperson_id, self.sale_order.user_id)
        self.assertEqual(entry.product_id, self.product)

        # price = 100, cost = 60, margin = 40, qty = 5 => 200 base
        # commission 10% => 20
        self.assertEqual(entry.unit_sale_price, 100.0)
        self.assertEqual(entry.unit_cost, 60.0)
        self.assertEqual(entry.unit_margin, 40.0)
        self.assertEqual(entry.margin_base, 200.0)
        self.assertEqual(entry.commission_amount, 20.0)

    def test_no_commission_entry_when_feature_disabled(self):
        self.company.enable_product_commission = False

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 3.0,
                'price_unit': 100.0,
            })]
        })
        sale_order.action_confirm()
        sale_line = sale_order.order_line[:1]

        self._validate_delivery(sale_order, qty_done=3.0)

        entries = self.env['sale.commission.entry'].search([
            ('sale_order_line_id', '=', sale_line.id)
        ])
        self.assertFalse(entries, "No commission entry should be created when feature is disabled.")

    def test_commission_entry_created_for_partial_delivery(self):
        self._validate_delivery(self.sale_order, qty_done=2.0)

        entries = self.env['sale.commission.entry'].search([
            ('sale_order_line_id', '=', self.sale_line.id)
        ])

        self.assertEqual(len(entries), 1, "One commission entry should be created for partial delivery.")

        entry = entries[0]
        self.assertEqual(entry.quantity, 2.0)

        # margin = (100 - 60) = 40
        # base = 40 * 2 = 80
        # commission = 8
        self.assertEqual(entry.margin_base, 80.0)
        self.assertEqual(entry.commission_amount, 8.0)
