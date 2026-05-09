"""
Tests for the discrepancy report and PDF generation.

Covers:
  - Discrepancy lines are correctly identified
  - Report renders without error (smoke test)
  - Export action returns act_url
  - Value of difference calculation
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("pharmacy_count", "post_install", "-at_install")
class TestDiscrepancyReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.location = cls.warehouse.lot_stock_id

        cls.product_x = cls.env["product.product"].create({
            "name": "Product X",
            "type": "product",
            "standard_price": 10.0,
        })
        cls.product_y = cls.env["product.product"].create({
            "name": "Product Y",
            "type": "product",
            "standard_price": 20.0,
        })

    def _make_validated_count(self):
        count = self.env["pharmacy.count"].create({
            "count_type": "periodic",
            "warehouse_id": self.warehouse.id,
        })
        self.env["pharmacy.count.line"].create([
            {
                "count_id": count.id,
                "product_id": self.product_x.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 80.0,
                "counted_status": "counted",
                "reason": "20 units expired",
            },
            {
                "count_id": count.id,
                "product_id": self.product_y.id,
                "location_id": self.location.id,
                "expected_qty": 50.0,
                "counted_qty": 50.0,
                "counted_status": "counted",
            },
        ])
        count.action_validate()
        return count

    def test_only_discrepancy_lines_have_nonzero_difference(self):
        count = self._make_validated_count()
        discrepancy = count.line_ids.filtered(lambda l: l.difference != 0)
        self.assertEqual(len(discrepancy), 1)
        self.assertEqual(discrepancy.product_id, self.product_x)

    def test_discrepancy_value_calculation(self):
        count = self._make_validated_count()
        line = count.line_ids.filtered(lambda l: l.product_id == self.product_x)
        # difference = 80 - 100 = -20; value = -20 * 10 = -200
        self.assertAlmostEqual(line.difference_value, -200.0, places=2)

    def test_smart_button_count_matches_discrepancy_lines(self):
        count = self._make_validated_count()
        self.assertEqual(count.discrepancy_lines, 1)

    def test_export_discrepancy_action_returns_act_url(self):
        count = self._make_validated_count()
        action = count.action_export_discrepancy_excel()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn(str(count.id), action["url"])

    def test_pdf_report_action_exists(self):
        """Smoke test: the report action resolves without error."""
        count = self._make_validated_count()
        report_action = self.env.ref(
            "pharmacy_inventory_ops.action_report_pharmacy_count"
        )
        self.assertTrue(report_action.exists())
        # Render HTML (lighter than PDF for CI)
        html_content, content_type = self.env["ir.actions.report"]._render_qweb_html(
            "pharmacy_inventory_ops.report_pharmacy_count_template",
            count.ids,
        )
        self.assertIn(b"Pharmacy Inventory Count", html_content)
        self.assertIn(b"Discrepancy Report", html_content)

    def test_pdf_report_contains_reason(self):
        count = self._make_validated_count()
        html_content, _ = self.env["ir.actions.report"]._render_qweb_html(
            "pharmacy_inventory_ops.report_pharmacy_count_template",
            count.ids,
        )
        self.assertIn(b"20 units expired", html_content)

    def test_pdf_report_shows_summary_for_periodic(self):
        count = self._make_validated_count()
        html_content, _ = self.env["ir.actions.report"]._render_qweb_html(
            "pharmacy_inventory_ops.report_pharmacy_count_template",
            count.ids,
        )
        self.assertIn(b"Total Products", html_content)
        self.assertIn(b"With Discrepancy", html_content)

    def test_discrepancy_view_action_opens_filtered_lines(self):
        count = self._make_validated_count()
        action = count.action_view_discrepancy_lines()
        self.assertEqual(action["res_model"], "pharmacy.count.line")
        self.assertIn(("difference", "!=", 0), action["domain"])
        self.assertIn(("count_id", "=", count.id), action["domain"])

