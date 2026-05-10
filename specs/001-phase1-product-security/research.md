# Research: Phase 1 Product Management Security

## Research Areas & Decisions

### 1. Immutable Logging for Security Events
**Decision**: Utilize Odoo's built-in `mail.thread` (Chatter) with customized access rules, or a dedicated immutable custom log model if `mail.thread` cannot be made strictly immutable for certain events.
**Rationale**: Odoo's chatter already tracks field changes automatically when configured. To ensure immutability, we will enforce `unlink` restrictions on the underlying `mail.message` / `mail.tracking.value` for the specific models, or create a simple append-only `pharmacy.audit.log` table if chatter restrictions are too broad.
**Alternatives considered**: 
- Native `mail.thread` without changes (rejected: users with certain rights can delete messages).
- External logging service (rejected: out of scope, architectural change).

### 2. Protecting Sensitive Fields from Unauthorized RPC Access
**Decision**: Override the `read()` and `write()` methods on the product models to explicitly check user groups before returning or modifying sensitive fields (e.g., cost, commission). If an unauthorized user requests these fields, either strip them from the result (for `read`) or raise an AccessError (for `write`). Also remove fields from UI views using `groups="pharmacy_base.group_pricing_manager"`.
**Rationale**: Relying only on XML view `groups` attribute does not protect the fields from being accessed or updated via XML-RPC/JSON-RPC. Overriding ORM methods ensures strict backend security.
**Alternatives considered**:
- Odoo's field-level security (`groups` attribute on the model field definition). This is actually the best native way. If `groups` is defined directly on the Python field `fields.Float(..., groups="pharmacy_base.group_pricing_manager")`, Odoo automatically handles RPC stripping and writing restrictions. We will use this as the primary method instead of overriding `read()`/`write()` where possible.

### 3. Backend Validation for Business Limits (Max Qty, Low-Stock)
**Decision**: Override `create` and `write` methods in the corresponding models (e.g., Sales Order Line or POS Order Line) or the specific wizard actions to validate quantities against the defined limits. Use `env.user.has_group()` to allow overrides only for authorized managers, and trigger an audit log on override.
**Rationale**: Limits must be strictly enforced at the backend. UI-only validation is insufficient.
**Alternatives considered**: Standard Odoo constraints (rejected: `_sql_constraints` cannot check user groups dynamically; `@api.constrains` can raise errors but cannot easily implement "manager override" workflows seamlessly without context passing).

### 4. Sudo() Usage Review
**Decision**: Grep for `.sudo()` across the `pharmacy_*` addons. Replace with `with_user()` or explicitly scope the sudo by isolating the exact operations that need elevation (like writing to the immutable log) and leaving the rest of the transaction under standard user rights.
**Rationale**: Unscoped `sudo()` is a common vulnerability leading to privilege escalation.

## Conclusion
All technical approaches rely on standard Odoo ORM security features (field-level `groups`, method overrides, `ir.model.access.csv`, and scoped `sudo()`). No new external dependencies are required. All `NEEDS CLARIFICATION` implicitly resolved by applying Odoo 18 Community best practices.
