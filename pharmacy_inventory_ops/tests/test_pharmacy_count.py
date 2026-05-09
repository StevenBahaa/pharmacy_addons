"""
Tests for pharmacy.count and pharmacy.count.line models.

Covers:
  - Daily spot-check creation and validation
  - Mandatory reason enforcement
  - Periodic count validation gates
  - Inventory adjustment on validation
  - State machine transitions
  - Summary computed fields
"""
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged("pharmacy_count", "post_install", "-at_install")
class TestPharmacyCountBase(TransactionCase):
    """Shared setUp for all pharmacy count tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Warehouse & location
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.location = cls.warehouse.lot_stock_id

        # Products
        cls.product_a = cls.env["product.product"].create({
            "name": "Paracetamol 500mg",
            "default_code": "PARA500",
            "type": "product",
            "barcode": "1234567890",
            "standard_price": 2.50,
        })
        cls.product_b = cls.env["product.product"].create({
            "name": "Amoxicillin 250mg",
            "default_code": "AMOX250",
            "type": "product",
            "barcode": "0987654321",
            "standard_price": 5.00,
        })
        cls.product_c = cls.env["product.product"].create({
            "name": "Ibuprofen 200mg",
            "default_code": "IBU200",
            "type": "product",
            "standard_price": 3.00,
        })

        # Put some stock in location
        cls._set_stock(cls.product_a, 100.0)
        cls._set_stock(cls.product_b, 50.0)
        cls._set_stock(cls.product_c, 0.0)

    @classmethod
    def _set_stock(cls, product, qty):
        """Helper: directly set on-hand quantity via quant."""
        quant = cls.env["stock.quant"].search([
            ("product_id", "=", product.id),
            ("location_id", "=", cls.location.id),
        ], limit=1)
        if quant:
            quant.with_context(inventory_mode=True, skip_pharmacy_reason_check=True).write(
                {"inventory_quantity": qty}
            )
            quant.with_context(skip_pharmacy_reason_check=True).action_apply_inventory()
        else:
            cls.env["stock.quant"].with_context(
                inventory_mode=True, skip_pharmacy_reason_check=True
            ).create({
                "product_id": product.id,
                "location_id": cls.location.id,
                "quantity": qty,
            })

    def _make_daily_count(self, lines_data=None):
        """Create a daily spot-check with optional lines_data list."""
        count = self.env["pharmacy.count"].create({
            "count_type": "daily",
            "warehouse_id": self.warehouse.id,
        })
        if lines_data:
            for ld in lines_data:
                self.env["pharmacy.count.line"].create({
                    "count_id": count.id,
                    **ld,
                })
        return count

    def _make_periodic_count(self, lines_data=None):
        """Create a periodic full count."""
        count = self.env["pharmacy.count"].create({
            "count_type": "periodic",
            "warehouse_id": self.warehouse.id,
        })
        if lines_data:
            for ld in lines_data:
                self.env["pharmacy.count.line"].create({
                    "count_id": count.id,
                    **ld,
                })
        return count


@tagged("pharmacy_count", "post_install", "-at_install")
class TestPharmacyCountCreation(TestPharmacyCountBase):
    """Test record creation and name sequence."""

    def test_daily_count_gets_sequence_name(self):
        count = self._make_daily_count()
        self.assertIn("PHC-DAILY", count.name)

    def test_periodic_count_gets_sequence_name(self):
        count = self._make_periodic_count()
        self.assertIn("PHC-PERD", count.name)

    def test_default_state_is_draft(self):
        count = self._make_daily_count()
        self.assertEqual(count.state, "draft")

    def test_count_date_defaults_to_today(self):
        from odoo.fields import Date
        count = self._make_daily_count()
        self.assertEqual(count.count_date, Date.today())

    def test_responsible_defaults_to_current_user(self):
        count = self._make_daily_count()
        self.assertEqual(count.responsible_id, self.env.user)


@tagged("pharmacy_count", "post_install", "-at_install")
class TestStateTransitions(TestPharmacyCountBase):
    """State machine: draft → in_progress → done / cancelled."""

    def test_action_start_moves_to_in_progress(self):
        count = self._make_daily_count()
        count.action_start()
        self.assertEqual(count.state, "in_progress")

    def test_cannot_start_already_in_progress_count(self):
        count = self._make_daily_count()
        count.action_start()
        with self.assertRaises(UserError):
            count.action_start()

    def test_cancel_from_draft(self):
        count = self._make_daily_count()
        count.action_cancel()
        self.assertEqual(count.state, "cancelled")

    def test_cancel_from_in_progress(self):
        count = self._make_daily_count()
        count.action_start()
        count.action_cancel()
        self.assertEqual(count.state, "cancelled")

    def test_cannot_cancel_validated_count(self):
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 100.0,
            "counted_status": "counted",
        }])
        count.action_validate()
        with self.assertRaises(UserError):
            count.action_cancel()

    def test_reset_to_draft_from_cancelled(self):
        count = self._make_daily_count()
        count.action_cancel()
        count.action_reset_draft()
        self.assertEqual(count.state, "draft")

    def test_cannot_reset_done_to_draft(self):
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 100.0,
            "counted_status": "counted",
        }])
        count.action_validate()
        with self.assertRaises(UserError):
            count.action_reset_draft()


@tagged("pharmacy_count", "post_install", "-at_install")
class TestDailySpotCheck(TestPharmacyCountBase):
    """INV-UC-05 — Daily Spot-Check acceptance criteria."""

    def test_validate_no_discrepancy_no_reason_required(self):
        """If counted == expected, no reason needed."""
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 100.0,
            "counted_status": "counted",
        }])
        # Should not raise
        count.action_validate()
        self.assertEqual(count.state, "done")

    def test_validate_with_discrepancy_requires_reason(self):
        """Discrepancy without reason → UserError."""
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 90.0,
            "counted_status": "counted",
            # No reason
        }])
        with self.assertRaises(UserError, msg="Should require reason for discrepancy"):
            count.action_validate()

    def test_validate_with_discrepancy_and_reason_succeeds(self):
        """Discrepancy + reason → validation succeeds."""
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 90.0,
            "counted_status": "counted",
            "reason": "10 units expired and disposed",
        }])
        count.action_validate()
        self.assertEqual(count.state, "done")

    def test_validation_updates_onhand_quantity(self):
        """After validation, the quant reflects counted_qty."""
        self._set_stock(self.product_a, 100.0)
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 85.0,
            "counted_status": "counted",
            "reason": "Damaged stock removed",
        }])
        count.action_validate()
        quant = self.env["stock.quant"].search([
            ("product_id", "=", self.product_a.id),
            ("location_id", "=", self.location.id),
        ], limit=1)
        self.assertAlmostEqual(quant.quantity, 85.0, places=2)

    def test_multiple_lines_all_need_reasons_if_discrepancy(self):
        """Only lines with discrepancy need reasons; others can be blank."""
        count = self._make_daily_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 95.0,
                "counted_status": "counted",
                # Missing reason — should fail
            },
            {
                "product_id": self.product_b.id,
                "location_id": self.location.id,
                "expected_qty": 50.0,
                "counted_qty": 50.0,
                "counted_status": "counted",
                # No discrepancy, no reason needed
            },
        ])
        with self.assertRaises(UserError):
            count.action_validate()

    def test_reason_recorded_in_chatter(self):
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 98.0,
            "counted_status": "counted",
            "reason": "Two units broken",
        }])
        count.action_validate()
        messages = count.message_ids.mapped("body")
        self.assertTrue(
            any("Two units broken" in (m or "") for m in messages),
            "Reason should appear in the chatter",
        )


@tagged("pharmacy_count", "post_install", "-at_install")
class TestPeriodicCount(TestPharmacyCountBase):
    """INV-UC-05 — Periodic Full Count acceptance criteria."""

    def test_periodic_cannot_validate_with_uncounted_lines(self):
        """Periodic count: all lines must be counted or not_found before validation."""
        count = self._make_periodic_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 100.0,
                "counted_status": "counted",
            },
            {
                "product_id": self.product_b.id,
                "location_id": self.location.id,
                "expected_qty": 50.0,
                # counted_status still 'not_started'
            },
        ])
        with self.assertRaises(UserError, msg="Should block on uncounted lines"):
            count.action_validate()

    def test_periodic_validates_when_all_lines_counted(self):
        count = self._make_periodic_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 100.0,
                "counted_status": "counted",
            },
            {
                "product_id": self.product_b.id,
                "location_id": self.location.id,
                "expected_qty": 50.0,
                "counted_qty": 50.0,
                "counted_status": "counted",
            },
        ])
        count.action_validate()
        self.assertEqual(count.state, "done")

    def test_periodic_validates_with_not_found_lines(self):
        """Not-found lines count as 'counted' for the gate check."""
        count = self._make_periodic_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 100.0,
                "counted_status": "counted",
            },
            {
                "product_id": self.product_c.id,
                "location_id": self.location.id,
                "expected_qty": 0.0,
                "counted_qty": 0.0,
                "counted_status": "not_found",
                "reason": "Product not found on shelf",
            },
        ])
        count.action_validate()
        self.assertEqual(count.state, "done")

    def test_periodic_discrepancy_requires_reason(self):
        count = self._make_periodic_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 80.0,
                "counted_status": "counted",
                # No reason → should fail
            },
        ])
        with self.assertRaises(UserError):
            count.action_validate()

    def test_summary_counts_are_correct(self):
        count = self._make_periodic_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 95.0,
                "counted_status": "counted",
                "reason": "Shrinkage",
            },
            {
                "product_id": self.product_b.id,
                "location_id": self.location.id,
                "expected_qty": 50.0,
                "counted_qty": 50.0,
                "counted_status": "counted",
            },
            {
                "product_id": self.product_c.id,
                "location_id": self.location.id,
                "expected_qty": 0.0,
                # not_started
            },
        ])
        self.assertEqual(count.total_lines, 3)
        self.assertEqual(count.counted_lines, 2)
        self.assertEqual(count.not_counted_lines, 1)
        self.assertEqual(count.discrepancy_lines, 1)

    def test_progress_percentage(self):
        count = self._make_periodic_count(lines_data=[
            {
                "product_id": self.product_a.id,
                "location_id": self.location.id,
                "expected_qty": 100.0,
                "counted_qty": 100.0,
                "counted_status": "counted",
            },
            {
                "product_id": self.product_b.id,
                "location_id": self.location.id,
                "expected_qty": 50.0,
                # not_started
            },
        ])
        self.assertAlmostEqual(count.count_progress, 50.0, places=1)


@tagged("pharmacy_count", "post_install", "-at_install")
class TestCountLine(TestPharmacyCountBase):
    """Tests for pharmacy.count.line business logic."""

    def test_difference_computed_correctly(self):
        count = self._make_daily_count()
        line = self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 75.0,
            "counted_status": "counted",
        })
        self.assertAlmostEqual(line.difference, -25.0, places=2)

    def test_difference_value_uses_standard_price(self):
        count = self._make_daily_count()
        line = self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 90.0,
            "counted_status": "counted",
        })
        # product_a standard_price = 2.50; difference = -10
        self.assertAlmostEqual(line.difference_value, -10 * 2.50, places=2)

    def test_difference_zero_when_counted_not_entered(self):
        count = self._make_daily_count()
        line = self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_status": "not_started",
        })
        self.assertEqual(line.difference, 0.0)

    def test_mark_not_found_sets_status_and_qty(self):
        count = self._make_daily_count()
        line = self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product_b.id,
            "location_id": self.location.id,
            "expected_qty": 50.0,
        })
        line.action_mark_not_found()
        self.assertEqual(line.counted_status, "not_found")
        self.assertEqual(line.counted_qty, 0.0)
        self.assertTrue(line.reason)

    def test_reset_line_clears_counted_data(self):
        count = self._make_daily_count()
        line = self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
            "counted_qty": 90.0,
            "counted_status": "counted",
            "reason": "Test reason",
        })
        line.action_reset_line()
        self.assertEqual(line.counted_status, "not_started")
        self.assertFalse(line.reason)

    def test_barcode_lookup_returns_line_id(self):
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
        }])
        result = count.find_line_by_barcode("1234567890")
        self.assertIn("line_id", result)
        self.assertEqual(result["product_name"], self.product_a.display_name)

    def test_barcode_lookup_unknown_barcode_returns_error(self):
        count = self._make_daily_count()
        result = count.find_line_by_barcode("UNKNOWN_BARCODE_XYZ")
        self.assertIn("error", result)

    def test_barcode_lookup_product_not_in_count_returns_error(self):
        count = self._make_daily_count(lines_data=[{
            "product_id": self.product_a.id,
            "location_id": self.location.id,
            "expected_qty": 100.0,
        }])
        # product_b has barcode 0987654321 but is NOT in the count
        result = count.find_line_by_barcode("0987654321")
        self.assertIn("error", result)
