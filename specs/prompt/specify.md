Refine the existing Phase 2 security specification only.
Do not rewrite the entire document.
Append the following missing security requirements and acceptance criteria.

Add a new subsection under Functional Requirements:

### Advanced Security Hardening Requirements

- Restricted related models MUST never cause AccessError on pages that authorized users are allowed to open.
- One2many fields, stat buttons, smart buttons, notebook pages, compute fields, search_count, and related actions referencing restricted models MUST be protected using:
  - groups
  - has_group()
  - guarded compute logic
  - scoped sudo only after authorization validation
- Unauthorized users MUST NOT trigger reads of restricted models during normal page rendering.

- All export surfaces MUST be audited:
  - export_data
  - XLS export
  - PDF export
  - search_read
  - read_group
  - name_search
  - RPC payloads
  - POS payloads
  - JSON/controller responses

- Sensitive actions requiring explicit backend has_group() validation include:
  - Run Expiry Detection
  - Transfer Selected Expired Medicines
  - Force Unreserve
  - Validate Bulk Scrap
  - Create Consignment Vendor Bill
  - Import PO Lines
  - Create PO from Shortage List
  - Wishlist CALL CUSTOMER actions
  - Shared Barcode Approval
  - Make Reciprocal Related Product

- sudo() MUST be reviewed case-by-case.
- sudo() MUST NOT be automatically replaced with with_user().
- User-triggered sensitive actions require authorization validation before sudo usage.

- Immutable logs/history models MUST prevent normal write/unlink access:
  - discount history
  - consignment payment history
  - bulk scrap history
  - expiry transfer logs
  - shortage removal logs
  - wishlist state history

- Record rule implementation MUST explicitly cover:
  - expired medicine rows
  - expired locations
  - shortage list
  - wishlist
  - bulk scrap sessions
  - periodic inventory count sessions
  - stock reservation helpers
  - consignment records
  - forecast rows
  - PO tracking helper models

Add additional Success Criteria:

- Unauthorized users cannot access sensitive data through UI, RPC, exports, reports, controllers, or POS payloads.
- Allowed pages do not fail due to hidden restricted related models.
- Branch/company/location isolation works correctly for all protected Phase 2 models.
- No unrestricted transient wizard access remains.