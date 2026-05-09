"""
Tests for pharmacy.count.wizard (Periodic Count creation wizard).

Covers:
  - Wizard creates count with correct lines from quants
  - Warehouse/category/location filters work correctly
  - Products with zero qty are included
  - Error raised when no products match filters
"""
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged("pharmacy_count", "post_install", "-at_install")
class TestPeriodicCountWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.location = cls.warehouse.lot_stock_id

        # Categories
        cls.category_pharma = cls.env["product.category"].create({
            "name": "Pharmaceuticals",
        })
        cls.category_other = cls.env["product.category"].create({
            "name": "Other Goods",
        })

        # Products
        cls.prod_pharma_1 = cls.env["product.product"].create({
            "name": "Drug Alpha",
            "type": "product",
            "categ_id": cls.category_pharma.id,
        })
        cls.prod_pharma_2 = cls.env["product.product"].create({
            "name": "Drug Beta",
            "type": "product",
            "categ_id": cls.category_pharma.id,
        })
        cls.prod_other = cls.env["product.product"].create({
            "name": "Office Supplies",
            "type": "product",
            "categ_id": cls.category_other.id,
        })

        # Set stock
        for prod, qty in [
            (cls.prod_pharma_1, 200.0),
            (cls.prod_pharma_2, 100.0),
            (cls.prod_other, 30.0),
        ]:
            cls.env["stock.quant"].with_context(
                inventory_mode=True, skip_pharmacy_reason_check=True
            ).create({
                "product_id": prod.id,
                "location_id": cls.location.id,
                "quantity": qty,
            })

    def _run_wizard(self, **kwargs):
        defaults = {
            "warehouse_id": self.warehouse.id,
        }
        defaults.update(kwargs)
        wizard = self.env["pharmacy.count.wizard"].create(defaults)
        return wizard.action_create_count()

    # ------------------------------------------------------------------ #
    def test_wizard_creates_count_record(self):
        action = self._run_wizard()
        self.assertEqual(action["res_model"], "pharmacy.count")
        count = self.env["pharmacy.count"].browse(action["res_id"])
        self.assertTrue(count.exists())
        self.assertEqual(count.count_type, "periodic")
        self.assertEqual(count.state, "in_progress")

    def test_wizard_includes_all_stocked_products(self):
        action = self._run_wizard()
        count = self.env["pharmacy.count"].browse(action["res_id"])
        product_ids = count.line_ids.mapped("product_id").ids
        self.assertIn(self.prod_pharma_1.id, product_ids)
        self.assertIn(self.prod_pharma_2.id, product_ids)
        self.assertIn(self.prod_other.id, product_ids)

    def test_wizard_expected_qty_from_quant(self):
        action = self._run_wizard()
        count = self.env["pharmacy.count"].browse(action["res_id"])
        line = count.line_ids.filtered(
            lambda l: l.product_id == self.prod_pharma_1
        )
        self.assertTrue(line)
        self.assertAlmostEqual(line[0].expected_qty, 200.0, places=2)

    def test_wizard_filters_by_category(self):
        action = self._run_wizard(category_id=self.category_pharma.id)
        count = self.env["pharmacy.count"].browse(action["res_id"])
        product_ids = count.line_ids.mapped("product_id").ids
        self.assertIn(self.prod_pharma_1.id, product_ids)
        self.assertIn(self.prod_pharma_2.id, product_ids)
        self.assertNotIn(self.prod_other.id, product_ids)

    def test_wizard_filters_by_location(self):
        """When specific location given, lines should be for that location."""
        action = self._run_wizard(location_id=self.location.id)
        count = self.env["pharmacy.count"].browse(action["res_id"])
        locations = count.line_ids.mapped("location_id")
        for loc in locations:
            self.assertEqual(loc, self.location)

    def test_wizard_stores_warehouse_on_count(self):
        action = self._run_wizard()
        count = self.env["pharmacy.count"].browse(action["res_id"])
        self.assertEqual(count.warehouse_id, self.warehouse)

    def test_wizard_stores_category_on_count(self):
        action = self._run_wizard(category_id=self.category_pharma.id)
        count = self.env["pharmacy.count"].browse(action["res_id"])
        self.assertEqual(count.category_id, self.category_pharma)

    def test_wizard_lines_default_to_not_started(self):
        action = self._run_wizard()
        count = self.env["pharmacy.count"].browse(action["res_id"])
        for line in count.line_ids:
            self.assertEqual(
                line.counted_status, "not_started",
                f"Line for {line.product_id.name} should start as 'not_started'",
            )

    def test_wizard_no_products_raises_user_error(self):
        """Creating a count with a location that has no stock → UserError."""
        empty_location = self.env["stock.location"].create({
            "name": "Empty Shelf",
            "usage": "internal",
            "location_id": self.warehouse.view_location_id.id,
        })
        wizard = self.env["pharmacy.count.wizard"].create({
            "warehouse_id": self.warehouse.id,
            "location_id": empty_location.id,
            # category that has NO matching products in stock
            "category_id": self.env["product.category"].create({
                "name": "Empty Category",
            }).id,
        })
        with self.assertRaises(UserError):
            wizard.action_create_count()


@tagged("pharmacy_count", "post_install", "-at_install")
class TestMarkNotFoundWizard(TransactionCase):
    """Tests for the bulk 'Mark as Not Found' wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.location = cls.warehouse.lot_stock_id
        cls.product = cls.env["product.product"].create({
            "name": "Vitamin C",
            "type": "product",
        })

    def test_mark_not_found_wizard_updates_lines(self):
        count = self.env["pharmacy.count"].create({
            "count_type": "periodic",
            "warehouse_id": self.warehouse.id,
        })
        line = self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product.id,
            "location_id": self.location.id,
            "expected_qty": 10.0,
        })
        wizard = self.env["pharmacy.count.not.found.wizard"].create({
            "count_id": count.id,
            "line_ids": [(4, line.id)],
            "reason": "Missing from shelf during audit",
        })
        wizard.action_confirm()
        self.assertEqual(line.counted_status, "not_found")
        self.assertEqual(line.counted_qty, 0.0)
        self.assertEqual(line.reason, "Missing from shelf during audit")

    def test_mark_not_found_requires_at_least_one_line(self):
        count = self.env["pharmacy.count"].create({
            "count_type": "periodic",
            "warehouse_id": self.warehouse.id,
        })
        wizard = self.env["pharmacy.count.not.found.wizard"].create({
            "count_id": count.id,
            "reason": "Test",
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()
