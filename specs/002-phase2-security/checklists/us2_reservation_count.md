# UC Coverage Checklist: User Story 2 - Stock Reservation & Inventory Count

## SC4-UC-01: Stock Reservation & Transfer Locking
- [x] **ACL**: Verified in Phase 2. Logs and Wizards restricted.
- [x] **Record Rules**: Multi-company isolation implemented for logs.
- [x] **Backend Checks**: `action_force_unreserve` guarded in wizard.
- [x] **Sudo**: Reviewed `reserve_for_picking` and `release_for_picking` in `stock.quant`.
- [ ] **Tests**: Negative test for Pharmacist trying to force unreserve.

## SC4-UC-02: Inventory Adjustment Daily & Periodic Count
- [x] **ACL**: Counts and Wizards restricted to Inventory/Pharmacy Manager.
- [x] **Record Rules**: Multi-company isolation implemented.
- [x] **Backend Checks**: Guarded `action_validate` in `pharmacy.count`.
- [x] **Sudo**: Reviewed `_apply_inventory_adjustments` in `pharmacy_count.py`.
- [ ] **Tests**: Verify Cashier cannot create or validate counts.

## SC4-UC-03: Bulk Scrap
- [x] **ACL**: Bulk scrap models restricted in Phase 2.
- [x] **Record Rules**: Multi-company isolation implemented (added `company_id`).
- [x] **Backend Checks**: Guarded `action_validate` in `pharmacy.bulk.scrap`.
- [x] **Sudo**: Reviewed `stock.scrap` creation logic in `bulk_scrap.py`.
- [ ] **Tests**: Negative test for Technician trying to validate scrap.

## SC4-UC-04: Forecast & Consumption Comparison
- [x] **ACL**: Models restricted or read-only for users in Phase 2.
- [x] **Backend Checks**: Guarded `action_create_purchase_order` in `product_forecast.py`.
- [ ] **Fields**: Protect cost/margin fields in forecast view if any.
- [ ] **Tests**: Verify only Purchasing/Pharmacy managers can trigger PO creation.

## SC4-UC-05: Reorder Threshold & Shortage List
- [x] **ACL**: Shortage list restricted in Phase 2.
- [x] **Record Rules**: Multi-company isolation implemented.
- [x] **Backend Checks**: Guarded `action_create_rfq` and `action_refresh_shortage_lines` in `pharmacy_shortage_line.py`.
- [ ] **Tests**: Negative test for direct RPC refresh attempt by Cashier.