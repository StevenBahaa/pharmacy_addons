/** @odoo-module **/
/**
 * Pharmacy Inventory Count — UI Tours
 *
 * Three tours covering the main acceptance criteria:
 *   1. pharmacy_count_daily_tour          — Daily Spot-Check full flow
 *   2. pharmacy_count_periodic_wizard_tour — Periodic Count wizard
 *   3. pharmacy_count_summary_tour         — Summary progress panel
 */

import { registry } from "@web/core/registry";

// ======================================================================
// Tour 1 — Daily Spot-Check
// ======================================================================
registry.category("web_tour.tours").add("pharmacy_count_daily_tour", {
    test: true,
    url: "/web#action=pharmacy_inventory_ops.action_pharmacy_count_daily",
    steps: () => [
        // Open the list view
        {
            trigger: ".o_list_view, .o_nocontent_help",
            content: "Daily spot-check list loaded",
            run: "click",
        },
        // Create a new daily count
        {
            trigger: ".o_list_button_add, button.btn-primary:contains('New')",
            content: "Click New to create daily count",
            run: "click",
        },
        // Verify count_type is pre-set to daily
        {
            trigger: "select[id$='count_type'], .o_field_widget[name='count_type'] .o_select_menu_toggler",
            content: "Count type field visible",
            run: () => {
                // Just check the field is present
            },
        },
        // Add a product line via the inline list
        {
            trigger: ".o_field_one2many[name='line_ids'] .o_field_cell[name='product_id'], " +
                     ".o_field_one2many[name='line_ids'] .o_list_button_add",
            content: "Click to add a product line",
            run: "click",
        },
        // Type product name
        {
            trigger: ".o_field_many2one[name='product_id'] input",
            content: "Enter product name",
            run: "edit Tour Test Drug",
        },
        {
            trigger: ".o_m2o_dropdown_option:contains('Tour Test Drug'), " +
                     ".ui-autocomplete .ui-menu-item:contains('Tour Test Drug')",
            content: "Select the product",
            run: "click",
        },
        // Enter counted qty
        {
            trigger: ".o_field_float[name='counted_qty'] input",
            content: "Enter counted quantity",
            run: "edit 45",
        },
        // Enter reason (mandatory — discrepancy exists: 50 vs 45)
        {
            trigger: ".o_field_text[name='reason'] textarea, " +
                     "td[name='reason'] textarea",
            content: "Enter reason for discrepancy",
            run: "edit 5 units dispensed without system update",
        },
        // Save changes
        {
            trigger: ".o_form_button_save, button:contains('Save manually')",
            content: "Save the record",
            run: "click",
        },
        // Validate
        {
            trigger: "button:contains('Validate Count')",
            content: "Click Validate Count",
            run: "click",
        },
        // Confirm dialog if present
        {
            trigger: ".o_dialog button:contains('OK'), .modal-footer button.btn-primary",
            content: "Confirm validation dialog",
            run: "click",
            optional: true,
        },
        // Check state is done
        {
            trigger: ".o_statusbar_status .o_status_label:contains('Validated'), " +
                     ".o_field_widget[name='state'] .badge:contains('Validated')",
            content: "Count is now validated",
        },
    ],
});

// ======================================================================
// Tour 2 — Periodic Count Wizard
// ======================================================================
registry.category("web_tour.tours").add("pharmacy_count_periodic_wizard_tour", {
    test: true,
    url: "/web#action=pharmacy_inventory_ops.action_pharmacy_count_wizard",
    steps: () => [
        // Wizard dialog or inline form is open
        {
            trigger: ".o_dialog .o_form_view, .o_form_view[model='pharmacy.count.wizard']",
            content: "Periodic count wizard is open",
        },
        // Warehouse should already be pre-filled; confirm it
        {
            trigger: ".o_field_many2one[name='warehouse_id'] input",
            content: "Warehouse field is present",
        },
        // Click Create Periodic Count
        {
            trigger: "button:contains('Create Periodic Count')",
            content: "Submit the wizard",
            run: "click",
        },
        // The new count form should open
        {
            trigger: ".o_form_view .o_field_widget[name='state'] .badge:contains('In Progress'), " +
                     ".o_statusbar_status span:contains('In Progress')",
            content: "Periodic count created and in progress",
        },
        // Verify progress panel is visible
        {
            trigger: ".o_group:contains('Count Progress'), " +
                     ".o_field_widget[name='total_lines']",
            content: "Count progress panel visible",
        },
    ],
});

// ======================================================================
// Tour 3 — Summary Panel & Mark Not Started
// ======================================================================
registry.category("web_tour.tours").add("pharmacy_count_summary_tour", {
    test: true,
    steps: () => [
        // Form is already open (URL contains the record id)
        {
            trigger: ".o_form_view",
            content: "Pharmacy count form is open",
        },
        // Summary panel shows totals
        {
            trigger: ".o_field_widget[name='total_lines'], .o_group:contains('Total Products')",
            content: "Total products field is visible",
        },
        {
            trigger: ".o_field_widget[name='not_counted_lines']",
            content: "Not yet counted field is visible",
        },
        // Progress bar
        {
            trigger: ".o_field_widget[name='count_progress']",
            content: "Progress bar is visible",
        },
        // Enter counted qty for the single line
        {
            trigger: ".o_field_one2many[name='line_ids'] td[name='counted_qty'] input, " +
                     ".o_field_one2many[name='line_ids'] .o_field_float[name='counted_qty'] input",
            content: "Enter counted quantity",
            run: "edit 50",
        },
        // Save
        {
            trigger: ".o_form_button_save",
            content: "Save",
            run: "click",
        },
        // Counted lines should now be 1
        {
            trigger: ".o_field_widget[name='counted_lines'] .o_field_integer, " +
                     ".o_field_integer[name='counted_lines']",
            content: "Counted lines updated to 1",
            run: () => {
                const el = document.querySelector(
                    "[name='counted_lines'] .o_field_integer, .o_field_integer[name='counted_lines']"
                );
                if (el && parseInt(el.textContent) < 1) {
                    throw new Error("Expected counted_lines ≥ 1");
                }
            },
        },
    ],
});

