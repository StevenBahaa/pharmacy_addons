
Update Phase 2 tasks only.

Append these additional final hardening tasks under Phase 7:

- PH2-POS-004 [P] Ensure One2many/stat button compute methods referencing restricted models return safe defaults for unauthorized users instead of triggering AccessError.
- PH2-POS-005 [P] Audit search_count and compute methods using restricted models and guard them with has_group() before reading protected records.
- PH2-REP-002 [P] Audit export_data and custom XLS/PDF export methods for hidden restricted field leakage.

Do not rewrite the file.
