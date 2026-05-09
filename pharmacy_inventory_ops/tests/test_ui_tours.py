"""
UI Tour tests for pharmacy inventory count.

These tests use Odoo's HttpCase / tour runner to exercise the actual
browser UI flows described in the acceptance criteria.

Each tour is defined both here (Python trigger) and in JS
(static/src/js/tours/ — defined inline as registry tours below).
"""
from odoo.tests import HttpCase, tagged


@tagged("pharmacy_count_ui", "post_install", "-at_install")
class TestPharmacyCountTours(HttpCase):

    def setUp(self):
        super().setUp()
        # Ensure base data exists
        self.warehouse = self.env.ref("stock.warehouse0")
        self.location = self.warehouse.lot_stock_id

        self.product_tour = self.env["product.product"].create({
            "name": "Tour Test Drug",
            "default_code": "TTD001",
            "type": "product",
            "barcode": "9990001234567",
            "standard_price": 5.0,
        })

        # Set on-hand quantity
        self.env["stock.quant"].with_context(
            inventory_mode=True, skip_pharmacy_reason_check=True
        ).create({
            "product_id": self.product_tour.id,
            "location_id": self.location.id,
            "quantity": 50.0,
        })

    # ------------------------------------------------------------------ #
    # Tour: Daily Spot-Check — create, add line, validate
    # ------------------------------------------------------------------ #
    def test_tour_daily_spot_check(self):
        self.start_tour(
            "/web#action=pharmacy_inventory_ops.action_pharmacy_count_daily",
            "pharmacy_count_daily_tour",
            login="admin",
        )

    # ------------------------------------------------------------------ #
    # Tour: Periodic Count Wizard — open wizard, fill, create
    # ------------------------------------------------------------------ #
    def test_tour_periodic_count_wizard(self):
        self.start_tour(
            "/web#action=pharmacy_inventory_ops.action_pharmacy_count_wizard",
            "pharmacy_count_periodic_wizard_tour",
            login="admin",
        )

    # ------------------------------------------------------------------ #
    # Tour: Count progress summary
    # ------------------------------------------------------------------ #
    def test_tour_count_summary(self):
        # Pre-create a periodic count so tour can open it
        count = self.env["pharmacy.count"].create({
            "count_type": "periodic",
            "warehouse_id": self.warehouse.id,
            "state": "in_progress",
        })
        self.env["pharmacy.count.line"].create({
            "count_id": count.id,
            "product_id": self.product_tour.id,
            "location_id": self.location.id,
            "expected_qty": 50.0,
        })
        self.start_tour(
            f"/web#model=pharmacy.count&id={count.id}&view_type=form",
            "pharmacy_count_summary_tour",
            login="admin",
        )

