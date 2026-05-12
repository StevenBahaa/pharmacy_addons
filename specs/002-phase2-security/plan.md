# Implementation Plan: Phase 2 Security Hardening

**Branch**: `[###-feature-name]` | **Date**: May 10, 2026
**Spec**: `/specs/002-phase2-security/spec.md`

## Summary

This plan outlines the detailed security audit, ACL adjustments, record rules, field visibility, backend method protections, POS backend validations, and `sudo()` reviews for Phase 2 pharmacy modules. The goal is to strictly restrict access to sensitive operations and data without redesigning architecture or workflows.

## Technical Context

**Language/Version**: Python 3.10+, Odoo 18 Community
**Primary Dependencies**: `pharmacy_base`, Phase 2 modules (e.g., `pharmacy_inventory_advanced`, `pharmacy_pos`, `pharmacy_purchase`, etc.)
**Storage**: PostgreSQL
**Testing**: Odoo standard unit tests (Python `unittest`)
**Target Platform**: Odoo Server / Web Client / POS
**Project Type**: Odoo Addons Security Hardening
**Constraints**: Do not redesign architecture, no UI workflow changes, minimal safe changes, strictly utilize existing `pharmacy_base` roles.

## Constitution Check

*Pass.* No architectural changes are made. Only existing groups from `pharmacy_base` are utilized.

## Delivery Order

1. Audit only
2. Manifest fixes
3. ACL fixes
4. Record rules
5. Menu/action/report restrictions
6. Field visibility
7. Backend checks
8. sudo review
9. POS backend security
10. Role testing
11. Final report

## Detailed Plans

### 1. Audit Plan
- Inspect all Phase 2 modules, manifests, ACL CSV files, security XML, and record rules.
- Inspect transient wizards, menus, actions, and reports.
- Inspect controllers/routes, POS-exposed backend methods, and `sudo()` usages.

### 2. Manifest Plan
- Ensure all Phase 2 modules depend on `pharmacy_base` if referencing pharmacy groups.
- Ensure security files load before views/actions.
- Verify `pharmacy_reports` ACL loading.

### 3. ACL Plan
Define explicit ACLs for all Phase 2 custom models:
- Last purchase discount history
- Shared barcode models & related product models
- Expired location/helper models & page/report models
- Expiry detection wizard/settings
- Purchase import helpers & consignment tracking/payment models
- PO tracking/report models
- Reservation helpers & inventory count models
- Bulk scrap and lines
- Forecast/consumption report models
- Shortage list
- Wishlist and wishlist lines/state logs

### 4. Record Rule Plan
Add branch/company/location isolation for:
- Expired medicine records & expired reports
- Shortage list & wishlist
- Bulk scrap sessions
- Consignment tracking
- Stock reservation helpers
- Forecast/report rows if stored
- Inventory count records
- Purchase/PO tracking if custom

### 5. Field Visibility Plan
Protect fields (hide from Cashier/Technician):
- Last purchase discount & discount history
- Box price/total expired report value
- Supplier discount data
- Consignment payment data
- Forecast/order cost data if any
- Customer wishlist sensitive data where appropriate

### 6. Backend Method Protection Plan
Add `has_group()` checks for:
- Shared barcode approval & make reciprocal related product
- Run expiry detection & transfer selected expired medicines
- Expired report export
- Import PO lines
- Consignment payment/vendor bill creation
- Force unreserve
- Validate bulk scrap & periodic count validation
- Create PO from shortage & manual remove shortage
- Wishlist create/call state changes
- Forecast Order Now shortcut

### 7. POS Security Plan
Backend validation for:
- Shared barcode selection
- Suggestions panel read-only data
- Expired lot warning override logging
- Wishlist creation permission
- Low-stock/availability enforcement if touched by Phase 2

### 8. sudo() Review Plan
Review `sudo()` in:
- Expiry detection & expired transfer
- Wishlist stock availability
- Purchase discount update
- Consignment tracking & reservation
- Shortage auto-add/remove
- Reports/exports

Classify each: safe system cron, safe log/activity creation, needs pre-check, unsafe bypass, remove/refactor.

### 9. Report/Menu/Export Plan
Secure:
- Expired Medicines Page & Report
- Shared Barcodes Report & Suggestions Performance
- Purchasing Discount Report
- Consignment Tracking & PO Tracking
- Bulk Scrap Report & Forecast/Consumption
- Shortage List & Wishlist CRM view
- Count/Discrepancy Report

### 10. Testing Plan
- **Role tests**: Cashier, Technician, Pharmacist, Inventory Manager, Purchasing Officer, Pricing Manager, Product Configuration Manager, Pharmacy Manager, Multi-Branch Manager, Compliance Manager.
- **Negative tests**: Unauthorized report access, unauthorized export, direct RPC bypass, branch/location leakage, POS payload leakage, wizard access leakage, unsafe sudo bypass, opening allowed pages must not fail.
  - Test that allowed pages open successfully for Cashier/Technician even when restricted related models exist.
  - Test no sensitive data leaks through UI, RPC, exports, reports, controllers, or POS payloads.
  - Test direct backend method calls by unauthorized users.
  - Test unauthorized transient wizard access.
  - Test branch/company/location isolation.