Refine the current Phase 2 implementation plan only.
Do not rewrite the whole plan.
Append or integrate the following requirements into the relevant sections.

Add to Audit Plan:

- Audit all One2many fields, stat buttons, smart buttons, notebook pages, compute fields, search_count methods, and related actions that reference restricted models.
- Ensure unauthorized users opening allowed pages do not trigger AccessError because of hidden restricted relations.
- Audit export_data, XLS export, PDF export, search_read, read_group, name_search, RPC, controllers, and POS payloads for sensitive data leakage.

Add to Backend Method Protection Plan:

- All user-triggered sensitive methods must check has_group() before performing work.
- If sudo() is required after authorization, use it only after the group check.
- Guard compute methods that count/read restricted models.

Add to Record Rule Plan:
Explicitly include record rules for:

- expired medicine rows
- expired locations
- shortage list
- wishlist
- bulk scrap sessions
- periodic count sessions
- stock reservation helpers
- consignment records
- forecast rows if stored
- PO tracking helper models if stored

Add to sudo() Review Plan:

- Do not automatically replace sudo() with with_user().
- Classify each sudo() case-by-case.
- Cron/system jobs may use scoped sudo for internal detection/log/activity creation.
- User-triggered actions must validate authorization before sudo.

Add to Testing Plan:

- Test that allowed pages open successfully for Cashier/Technician even when restricted related models exist.
- Test no sensitive data leaks through UI, RPC, exports, reports, controllers, or POS payloads.
- Test direct backend method calls by unauthorized users.
- Test unauthorized transient wizard access.
- Test branch/company/location isolation.
