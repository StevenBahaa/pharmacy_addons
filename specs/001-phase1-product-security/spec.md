# Feature Specification: Phase 1 Product Management Security

**Feature Branch**: `002-phase1-product-security`
**Created**: May 10, 2026
**Status**: Draft
**Input**: User description: "Create a complete security specification for Phase 1 Product Management use cases (UC-01 to UC-13)..."

## Security Goals
- Implement precise Role-Based Access Control (RBAC) for Phase 1 product management modules.
- Ensure `pharmacy_base/security/security.xml` remains the single source of truth for group definitions.
- Protect sensitive data (costs, margins, commissions) from unauthorized roles (Cashier, Technician).
- Enforce strict controls and audit trails for scheduled medicines, price overrides, and stock limits.

## Non-Goals
- No architectural redesigns or refactoring of existing business logic.
- No changes to model names, field names, menu structures, or UI design.
- No creation of new user groups outside of the centralized definitions.
- Out of scope: Any use cases beyond UC-01 to UC-13.

## Central Group Strategy
- **Source of Truth**: `pharmacy_base/security/security.xml`
- **Roles Referenced**: Pharmacy User, Cashier, Pharmacist, Pharmacist Technician, Inventory Manager, Pricing Manager, Product Configuration Manager, Pharmacy Manager, Compliance Manager.
- All other modules will reference these groups without duplicating them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure Basic Product Setup (UC-01 to UC-05) (Priority: P1)
As a Product Configuration Manager or Pharmacy Manager, I must be the only one able to create or edit core product fields, types, barcodes, and categories, so that basic product data remains consistent and trustworthy. Cashiers and Pharmacists should only be able to read this data to perform sales.
**Why this priority**: Core product data integrity is the foundation of the pharmacy system.
**Independent Test**: Can be tested by logging in as a Cashier and attempting to edit a product name or category, verifying the system blocks it.
**Acceptance Scenarios**:
1. **Given** I am logged in as a Cashier, **When** I view a product, **Then** all core fields (name, classification, package type) are read-only.
2. **Given** I am a Product Configuration Manager, **When** I create a barcode, **Then** the creation is successful and logged.

### User Story 2 - Secure Sensitive Product Data (UC-07 to UC-09) (Priority: P1)
As a Pricing Manager or Pharmacy Manager, I must have exclusive access to view and edit cost prices, commissions, and government price locks, so that sensitive financial information is not leaked to general staff.
**Why this priority**: Cost and commission data are strictly confidential.
**Independent Test**: Login as a Cashier and ensure the average purchase cost and commission fields are invisible or explicitly read-only and masked on the frontend, and not accessible via RPC.
**Acceptance Scenarios**:
1. **Given** I am a Cashier, **When** I view a product, **Then** the Avg Purchase Cost and Commission % fields are not visible.
2. **Given** I am a Pharmacy Manager, **When** I override a government price lock, **Then** the action requires validation and creates an immutable audit log.

### User Story 3 - Secure Regulated Medicines (UC-06) (Priority: P1)
As a Compliance Manager or Pharmacy Manager, I need strict controls over scheduled medicines, ensuring that only authorized pharmacists can edit their schedule levels and all changes are strictly logged to comply with regulations.
**Why this priority**: Legal and compliance requirement.
**Independent Test**: Attempt to edit a scheduled medicine's level as an Inventory Manager; the action should be blocked.
**Acceptance Scenarios**:
1. **Given** I am a Pharmacist, **When** I update a scheduled medicine level, **Then** the change is saved and an immutable log entry is generated in the chatter.
2. **Given** an unauthorized user attempts to bypass UI restrictions via API, **When** they send an RPC write command to a scheduled medicine, **Then** the backend rejects the request.

### User Story 4 - Secure Inventory Limits and Expiry (UC-10 to UC-13) (Priority: P2)
As an Inventory Manager, I must control lot/serial tracking methods and expiry dates, and restrict sales limits to prevent stockouts and selling expired products.
**Why this priority**: Ensures stock accuracy and prevents the sale of expired or restricted quantities.
**Independent Test**: Verify that tracking method changes after stock movements are strictly blocked at the backend level.
**Acceptance Scenarios**:
1. **Given** a product has existing stock movements, **When** an Inventory Manager attempts to change its tracking method, **Then** the system throws a validation error.
2. **Given** a Cashier tries to override the Max Quantity Per Invoice, **When** they exceed the limit, **Then** a hard-block event is triggered and logged.

### Edge Cases
- What happens when a user holds multiple roles (e.g., Pharmacist and Pricing Manager)?
- How does the system handle an authorized RPC call that attempts to write to multiple protected fields simultaneously, where the user only has access to some?
- What happens if an automated cron job requires elevated access to process expiry dates, but needs to leave an audit trail?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST restrict Product Creation/Edit to Product Configuration Manager and Pharmacy Manager.
- **FR-002**: System MUST restrict barcode creation/generation (UC-03) without using unsafe escalation and restrict to authorized roles.
- **FR-003**: System MUST enforce a backend warning and confirmation log when changing product classification (UC-04) after stock movement.
- **FR-004**: System MUST make Scheduled Medicine fields (UC-06) editable only by Pharmacist/Pharmacy Manager, generating an immutable log for every change.
- **FR-005**: System MUST hide Avg Purchase Cost (UC-08) and Commission % (UC-09) from Cashier and Technician in all views, reports, and API responses.
- **FR-006**: System MUST enforce Max Quantity (UC-10) and Low-Stock limits (UC-11) via backend validation and log any overrides immutably.
- **FR-007**: System MUST block changes to Lot/Serial Tracking (UC-12) or Expiry Date logic (UC-13) after stock movement, enforced at the backend.
- **FR-008**: System MUST ensure all custom models have explicit ACLs and do not use empty generic groups unless intended for all internal users.

### Key Entities
- **Product Entity**: Core entity containing all sensitive fields (Cost, Price Lock, Commission, Scheduled Medicine level).
- **Barcode Entity**: Entity for barcode mappings.
- **Audit Log**: Entity storing immutable records of critical changes.

## Security Matrices

### Model ACL Matrix
- **Product Entity**: Read (All Users), Write/Create/Unlink (Product Configuration Manager, Pharmacy Manager).
- **Custom Entities (e.g., barcodes)**: Explicit Read/Write per role, no generic groups for sensitive tables.

### Field Visibility Matrix
- **Cost**: Read (Pricing Manager, Pharmacy Manager).
- **Commission**: Read/Write (Pricing Manager, Pharmacy Manager).
- **Scheduled Medicine Indicator**: Read (All Users), Write (Pharmacist, Pharmacy Manager).
- **Government Price Lock**: Read (All Users), Write (Pharmacy Manager).

### Wizard/Action/Report Security Matrix
- **Expiry Dashboard/Report**: Read (Inventory Manager, Pharmacy Manager, Compliance Manager).
- **Periodic Count Action**: Execute (Inventory Manager, Pharmacy Manager).
- **Margin/Commission Reports**: Read (Pricing Manager, Pharmacy Manager).

### Backend Protection & Privilege Review Requirements
- All UI button visibility restrictions MUST be duplicated in the backend business logic.
- Eliminate or scope any privilege escalation calls in barcode generation or expiry cron jobs. Ensure escalation does not bypass core authorization.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: 100% of the specified entities have explicit access control lists without using unrestricted groups.
- **SC-002**: 100% of sensitive fields (cost, commission) are inaccessible via backend API to unauthorized roles.
- **SC-003**: 100% of price and limit overrides successfully generate an immutable audit log entry.
- **SC-004**: Zero regressions in standard user workflows (sales, POS) for authorized personnel.

## Assumptions
- The 9 centralized user roles are already fully defined in the central security configuration.
- Immutable logs can be achieved via standard framework message tracking with appropriate deletion restrictions.
- Standard framework ORM methods will be overridden where field-level security cannot be achieved strictly via views.
