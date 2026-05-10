# UC Coverage Checklist: User Story 3 - Purchase Discounts & Import

## SC1-UC-01: Last Purchase Discount
- [x] **ACL**: Verified in Phase 2. Discount history restricted.
- [x] **Fields**: `x_last_purchase_discount` protected with groups in Python.
- [ ] **Tests**: Verify Cashier cannot see last purchase discount on product form.

## SC3-UC-01: Import Purchase Order Lines from Excel
- [x] **ACL**: PO lines import wizards restricted in Phase 2.
- [x] **Backend Checks**: standard Odoo import functionality is guarded by model-level ACLs corrected in Phase 2. Custom actions in PO are guarded.
- [ ] **Tests**: Negative test for Pharmacist trying to import PO lines.

## SC3-UC-02: Consignment Purchase
- [x] **ACL**: Consignment tracking/payment restricted in Phase 2.
- [x] **Record Rules**: Multi-company isolation implemented.
- [x] **Backend Checks**: Guarded `action_create_vendor_bill` (as `action_create_payment_bill`) and `action_track_stock` (as `action_open_consignment_tracking`).
- [x] **Sudo**: Reviewed consignment vendor bill creation logic in `consignment_track_wizard.py`.
- [ ] **Tests**: Verify only Purchasing/Accounting/Pharmacy managers can process payments.

## SC3-UC-03: Purchase Order Tracking
- [x] **ACL**: PO tracking models restricted in Phase 2.
- [x] **Record Rules**: standard Odoo company rules.
- [ ] **Tests**: Verify UI isolation for tracking screens.