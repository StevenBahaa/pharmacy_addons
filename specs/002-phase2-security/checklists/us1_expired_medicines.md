# UC Coverage Checklist: User Story 1 - Expired Medicines Handling

## SC2-UC-01: Expired Location Type
- [x] **ACL**: Verified in Phase 2. `stock.location` standard ACLs apply, with pharmacy managers having create/write.
- [x] **Record Rules**: standard Odoo company rules.
- [ ] **Fields**: Protect `is_expired_location` field in view.
- [x] **Backend Checks**: Manual expiry detection guarded in `stock.lot` cron method.
- [x] **Sudo**: Reviewed `action_transfer_to_expired` and traceability picking creation.
- [ ] **Tests**: Negative test for Cashier trying to flag a location as expired.

## SC2-UC-02: MM/YYYY Expiry Input
- [x] **ACL**: Verified in Phase 2. `stock.lot` write restricted to authorized roles.
- [x] **Record Rules**: standard Odoo company rules.
- [ ] **Fields**: `x_expiry_month_year` should be readonly for unauthorized users.
- [x] **Backend Checks**: Guarded via standard Odoo ACL on `stock.lot`.
- [x] **Sudo**: Reviewed normalized date creation.
- [ ] **Tests**: Negative test for Cashier trying to change expiry date.

## SC2-UC-03: Near-Expiry Alerts
- [x] **ACL**: Settings restricted to Pharmacy Manager in Phase 2.
- [ ] **Fields**: Threshold fields protected.
- [x] **Backend Checks**: Guarded via `res.config.settings` ACL.
- [x] **Sudo**: Reviewed in cron job.
- [ ] **Tests**: Verify only managers can see/configure thresholds.

## SC2-UC-04: Expired Lot Detection
- [x] **ACL**: Detection logs restricted in Phase 2.
- [x] **Backend Checks**: Implemented `has_group()` for manual detection run in `stock_lot.py`.
- [x] **Sudo**: Reviewed usages in cron.
- [ ] **Tests**: Negative test for Cashier trying to run detection.

## SC2-UC-05: Expired Medicines Page
- [x] **ACL**: Page and `stock.quant` search view restricted in Phase 2.
- [x] **Backend Checks**: Implemented `has_group()` for `action_transfer_to_expired` and wizard opening methods in `stock_quant.py`.
- [ ] **Fields**: Hide sensitive value fields from unauthorized users.
- [ ] **Tests**: Verify Cashier cannot access the menu or the records.

## SC2-UC-06: Expired Medicines Report
- [x] **ACL**: Report wizards restricted in Phase 2.
- [x] **Backend Checks**: Implemented `has_group()` for PDF report and Excel export generation.
- [x] **Fields**: Cost data masked in `_get_report_values` if user is not pricing/pharmacy manager.
- [ ] **Tests**: Negative test for direct RPC call to generate report.