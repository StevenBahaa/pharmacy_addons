# Feature Specification: Phase 2 Security Specification

**Feature Branch**: `[###-feature-name]`
**Created**: May 10, 2026
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Expired Medicines Handling (Priority: P1)

Inventory Manager or Pharmacy Manager must be able to securely handle expired medicines, including moving them to a restricted location, detecting them via a scheduled job, and viewing reports, while unauthorized users (e.g., Cashier) are blocked.

**Why this priority**: Managing expired stock is critical for compliance and safety in a pharmacy. Unauthorized access could lead to selling expired medicines.

**Independent Test**: Can be fully tested by creating expired products and verifying that only authorized roles can detect, view, and move them, while Cashiers are denied access.

**Acceptance Scenarios**:
1. **Given** an expired product, **When** a Cashier tries to access the Expired Medicines Page, **Then** access is denied.
2. **Given** an expired product, **When** a Pharmacy Manager tries to bulk transfer it to Scrap, **Then** the transfer is successful.

### User Story 2 - Stock Reservation & Inventory Count (Priority: P1)

Inventory Managers and Pharmacy Managers can force unreserve stock and perform periodic inventory counts.

**Why this priority**: Accurate inventory and reservation management are core to pharmacy operations and preventing stock discrepancies.

**Independent Test**: Can be tested by attempting to unreserve stock as different roles and verifying that backend constraints enforce access correctly.

**Acceptance Scenarios**:
1. **Given** a reserved stock, **When** an Inventory Manager uses Force Unreserve, **Then** the reservation is removed and logged.
2. **Given** a reserved stock, **When** a Cashier tries to Force Unreserve, **Then** access is denied.

### User Story 3 - Purchase Discounts & Import (Priority: P2)

Purchasing Officers and Pharmacy Managers can securely import PO lines, track orders, and view purchase discounts without exposing sensitive pricing data to Cashiers or Technicians.

**Why this priority**: Protects sensitive financial and pricing data from unauthorized staff.

**Independent Test**: Can be tested by importing a PO with a Purchasing Officer and verifying the action succeeds, while trying to view the discount history as a Cashier fails.

**Acceptance Scenarios**:
1. **Given** an Excel file of PO lines, **When** a Purchasing Officer imports it, **Then** the lines are added and the action is logged.
2. **Given** a product with a discount history, **When** a Cashier tries to view it, **Then** the discount history is hidden.

### User Story 4 - Product Configuration & Wishlist (Priority: P2)

Product Configuration Managers can manage shared barcodes and complementary products, while authorized users can handle customer wishlists.

**Why this priority**: Ensures product data integrity and tracks customer needs without unauthorized tampering.

**Independent Test**: Can be tested by setting up shared barcodes as a Configuration Manager and verifying POS Cashiers can only read them.

**Acceptance Scenarios**:
1. **Given** a shared barcode setup, **When** a Cashier tries to edit the barcode record, **Then** access is denied.
2. **Given** a customer request, **When** a POS user with Wishlist permission adds an item, **Then** the wishlist is updated correctly.

### Edge Cases

- What happens when a user has multiple roles with conflicting permissions?
- How does the system handle an unauthorized user opening a page where a related model is restricted (e.g., hiding related records to prevent `AccessError`)?
- What happens if the scheduled expiry detection runs while stock moves are being validated?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every Phase 2 custom model MUST have explicit ACL defined.
- **FR-002**: Empty `group_id` ACLs MUST NOT be used unless intentionally safe.
- **FR-003**: Unsafe `base.group_user` ACLs MUST be narrowed to appropriate pharmacy groups.
- **FR-004**: Every wizard and transient model MUST have explicit ACL.
- **FR-005**: Every sensitive action, button, or server action MUST have backend `has_group()` validation.
- **FR-006**: Every report, menu, and export MUST have appropriate group restrictions.
- **FR-007**: Record rules MUST be implemented for branch, company, and location-sensitive records.
- **FR-008**: All `sudo()` usages MUST be reviewed, scoped, and documented.
- **FR-009**: POS frontend restrictions MUST be backed by backend validation to prevent API bypass.
- **FR-010**: System MUST NOT trigger `AccessError` for unauthorized users opening allowed pages due to hidden restricted models; restricted relations/buttons MUST be hidden and compute methods guarded.

### Detailed Security Guidelines

- Restricted related models MUST never cause `AccessError` on pages that authorized users are allowed to open.
- One2many fields, stat buttons, smart buttons, notebook pages, compute fields, `search_count`, and related actions referencing restricted models MUST be protected using:
  - groups
  - `has_group()`
  - guarded compute logic
  - scoped `sudo` only after authorization validation
- Unauthorized users MUST NOT trigger reads of restricted models during normal operations.
- All export surfaces MUST be audited:
  - `export_data`
  - XLS export
  - PDF export
  - `search_read`
  - `read_group`
  - `name_search`
- `sudo()` MUST be reviewed case-by-case.
- `sudo()` MUST NOT be automatically replaced with `with_user()`.
- User-triggered sensitive actions require authorization validation.
- Immutable logs/history models MUST prevent normal write/unlink access:
  - discount history
  - consignment payment history
  - bulk scrap history
  - expiry transactions
- Record rule implementation MUST explicitly cover:
  - expired medicine rows
  - expired locations
  - shortage list
  - wishlist
  - bulk scrap sessions
  - periodic inventory count sessions

**Specific Use Case Requirements:**
- **FR-SC1-01**: Last Purchase Discount MUST be visible only to Purchasing Officer, Pricing Manager, and Pharmacy Manager.
- **FR-SC1-02**: Shared barcode setting MUST be editable only by Pharmacy Manager/Product Configuration Manager.
- **FR-SC1-03**: Similar/Complementary products MUST be editable only by Product Configuration Manager/Pharmacy Manager.
- **FR-SC2-01**: Expired location creation/edit MUST be restricted to Inventory/Pharmacy Managers.
- **FR-SC2-02**: Expiry date edit (MM/YYYY) MUST be restricted to Inventory Manager/authorized receiving users.
- **FR-SC2-03**: Near-Expiry Alerts threshold settings MUST be editable only by Inventory/Pharmacy Managers.
- **FR-SC2-04**: Expired Lot Detection manual run MUST be restricted to Inventory/Pharmacy Managers.
- **FR-SC2-05**: Expired Medicines Page and Report MUST be accessible only to Inventory/Pharmacy Managers.
- **FR-SC3-01**: Import PO Lines MUST be allowed only for Purchasing Officer/Pharmacy Manager.
- **FR-SC3-02**: Consignment flag MUST be editable before confirmation only by Purchasing Officer/Pharmacy Manager.
- **FR-SC3-03**: PO Tracking screen MUST be visible to Purchasing Officer/Pharmacy Manager.
- **FR-SC4-01**: Force Unreserve MUST be restricted to Inventory/Pharmacy Managers.
- **FR-SC4-02**: Periodic count wizard MUST be restricted to Inventory/Pharmacy Managers.
- **FR-SC4-03**: Bulk Scrap model/wizard/menu MUST be restricted to Inventory/Pharmacy Managers.
- **FR-SC4-04**: Forecast & Consumption and Reorder Threshold editable ONLY by Inventory/Pharmacy Managers.
- **FR-SC5-01**: POS Wishlist button and creation MUST validate permission in the backend.

### Key Entities

- **Security Groups**: Existing roles from `pharmacy_base` (Cashier, Pharmacist, Inventory Manager, etc.).
- **Access Control Lists (ACLs)**: Defines create, read, write, and unlink permissions per model per group.
- **Record Rules**: Defines row-level access (e.g., branch/location filtering).
- **Wizards & Actions**: Transient models and server actions requiring explicit security checks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Phase 2 custom models have explicit and correct ACL definitions.
- **SC-002**: 0 unauthorized access errors (`AccessError`) occur during normal operations by restricted roles (e.g., Cashier).
- **SC-003**: 100% of POS frontend restrictions are mirrored by backend security validations.
- **SC-004**: All branch/location-sensitive records are correctly filtered based on user assignments.
- **SC-005**: All sensitive actions (e.g., Bulk Scrap, Force Unreserve) are inaccessible and un-executable by unauthorized roles.
- **SC-006**: Unauthorized users cannot access sensitive data through UI, RPC, exports, reports, controllers, or POS payloads.
- **SC-007**: Allowed pages do not fail due to hidden restricted related models.
- **SC-008**: Branch/company/location isolation works correctly for all protected Phase 2 models.
- **SC-009**: No unrestricted transient wizard access remains.

## Assumptions

- Uses centralized groups from `pharmacy_base` only; no new groups will be created.
- The architecture, business logic, UI design, workflows, model names, and field names will NOT be changed.
- The project is using Odoo 18 Community.
- `pharmacy_reports/security/ir.model.access.csv` exists and can be modified or verified.oups will be created.
- The architecture, business logic, UI design, workflows, model names, and field names will NOT be changed.
- The project is using Odoo 18 Community.
- `pharmacy_reports/security/ir.model.access.csv` exists and can be modified or verified.