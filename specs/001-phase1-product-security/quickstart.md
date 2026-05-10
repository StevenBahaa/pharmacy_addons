# Quickstart: Phase 1 Product Management Security

## Setup & Testing Instructions

1. **Apply the Module Updates**:
   Update all `pharmacy_*` modules in your local Odoo environment.
   ```bash
   odoo-bin -c odoo.conf -u pharmacy_base,pharmacy_inventory_advanced,pharmacy_inventory_ops,pharmacy_pos,pharmacy_purchase,pharmacy_reports,pharmacy_sales_rules,pharmacy_stock_expiry,pharmacy_stock_reservation,pharmacy_system,pharmacy_wishlist
   ```

2. **Verify Central Groups**:
   Go to Settings -> Users & Companies -> Groups.
   Filter by `pharmacy_base`. Ensure all 9 central roles are present and correctly mapped.

3. **Role-Based Testing**:
   Create or use test users assigned exclusively to each role (e.g., `test_cashier`, `test_pricing_manager`).
   
   *Test 1 (Cashier)*: Log in as Cashier. Navigate to a product. Verify that "Avg Purchase Cost" and "Commission %" fields are completely missing from the view.
   
   *Test 2 (Pharmacist)*: Log in as Pharmacist. Navigate to a product. Modify the "Schedule Level". Verify the change is allowed and a log entry appears in the chatter.
   
   *Test 3 (Negative Test)*: As a Cashier, attempt to export products or run a price report. Ensure an AccessError is raised.

4. **Verify Audit Logs**:
   Perform a government price lock override as a Pharmacy Manager. Check the chatter or the audit log model to confirm an immutable record was created detailing the previous and new values.
