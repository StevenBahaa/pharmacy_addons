# Research: Phase 2 Security Hardening

## Decisions

### 1. Approach to UI visibility vs Backend validation
**Decision**: Apply `groups="..."` to views and `has_group()` to all python methods (controllers, server actions, standard methods). For `compute` fields, guard logic with `has_group()` to avoid `AccessError` when reading records in contexts where related models are hidden.
**Rationale**: Fulfills FR-009, FR-010, and advanced security hardening requirements.

### 2. Sudo usage pattern
**Decision**: Audit all `sudo()` usages and explicitly wrap them in authorization pre-checks instead of automatically replacing with `with_user()`.
**Rationale**: `with_user()` can introduce bypasses if not carefully reviewed, and user-triggered actions need explicit validation.

### 3. Record rule isolation
**Decision**: Apply strict standard Odoo record rules (`['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]`) plus branch restrictions for custom models.
**Rationale**: Meets requirement to support multi-company/multi-branch setups out of the box in `pharmacy_base`.