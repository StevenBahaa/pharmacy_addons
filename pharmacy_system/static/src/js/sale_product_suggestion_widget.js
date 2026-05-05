/** @odoo-module **/

import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";

// ── Extend Many2OneField with an extra wrapper ──────────────────────────────

export class SaleProductSuggestionField extends Many2OneField {
    // Keep the SAME template as parent — we will NOT override it.
    // Instead we inject the icon via a sibling element rendered by the list cell.
}

SaleProductSuggestionField.supportedTypes = ["many2one"];

export const saleProductSuggestionField = {
    ...many2OneField,
    component: SaleProductSuggestionField,
    // We do not change extractProps or anything else
};

registry
    .category("fields")
    .add("sale_product_with_suggestion", saleProductSuggestionField);