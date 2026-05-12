# Data Model & State Transitions: Phase 1 Product Management Security

This feature does not introduce new core business entities but secures existing ones.

## 1. Product Entity (`product.template` / `product.product`)
**Role**: The central entity representing medications and non-medical products.
**Protected Attributes**:
- `standard_price` (Avg Purchase Cost) - Restricted to Pricing/Pharmacy Managers.
- `pharmacist_price` - Restricted to Pricing/Pharmacy Managers.
- `commission_pct` - Restricted to Pricing/Pharmacy Managers.
- `public_price` - Writable only by Pricing/Pharmacy Managers.
- `government_price_lock` - Writable only by Pharmacy Manager.
- `is_scheduled_medicine` & `schedule_level` - Writable only by Pharmacist/Pharmacy Manager.
- `max_qty_per_invoice` & `low_stock_limit` - Writable only by Product Configuration Manager/Pharmacy Manager.
- `tracking` (Lot/Serial) - Blocked from changing if stock moves exist.
- `classification` (Medicine/Non-Medicine) - Blocked from changing without warning if stock moves exist.

**State Transitions & Validations**:
- *Update Tracking/Classification*: Before allowing write, system checks for existing `stock.move.line`. If exists, tracking write is hard-blocked. Classification write logs a warning/confirmation.

## 2. Barcode Entity (`product.barcode.line`)
**Role**: Maps multiple barcodes to a product.
**Protected Attributes**:
- All fields (creation/modification/deletion) restricted to Product Configuration Manager, Inventory Manager, and Pharmacy Manager.
- Read access granted to POS and Cashier roles for scanning.

## 3. Audit Log Entity
**Role**: Immutable record of critical security events (overrides, scheduled medicine changes).
**Attributes**:
- `user_id` (User who performed action)
- `model_id` / `res_id` (Target record)
- `action_type` (e.g., "PRICE_OVERRIDE", "SCHEDULED_MEDICINE_CHANGE")
- `old_value` / `new_value`
- `timestamp`
**State Transitions & Validations**:
- Strictly Append-Only (`create` allowed for system/sudo, `write` and `unlink` blocked for all users).
