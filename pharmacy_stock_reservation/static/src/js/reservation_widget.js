/** @odoo-module **/
/**
 * pharmacy_stock_reservation/static/src/js/reservation_widget.js
 *
 * OWL widget: live "On Hand | Reserved | Available" summary
 * rendered as a stat-button-style inline display.
 *
 * FIXES vs previous version:
 * ─────────────────────────────────────────────────────────────────────────
 * FIX-1  Removed manual registry.category("owl_templates").add() call.
 *        In Odoo 18 OWL components use the xml`...` tagged template literal
 *        declared directly on the static `template` property — no separate
 *        template registry call is needed or supported.
 *
 * FIX-2  Removed __nextAnimationFrame__ destructure from owl (does not exist).
 *
 * FIX-3  formatFloat import corrected:
 *        Odoo 18: import from "@web/views/fields/formatters" is removed.
 *        Use: import { formatFloat } from "@web/core/utils/numbers"
 *        Or simply use Number.toFixed() for display — simpler and safer.
 *
 * FIX-4  Component props pattern updated to Odoo 18 OWL 2 style.
 *        Static props validation uses the Props object pattern.
 *
 * FIX-5  registry.category("fields").add() pattern kept — this is valid
 *        in Odoo 18 for registering custom field widgets.
 */

import { registry }     from "@web/core/registry";
import { Component,
         useState,
         onWillStart }  from "@odoo/owl";
import { useService }   from "@web/core/utils/hooks";
import { xml }          from "@odoo/owl";

export class PharmacyStockSummaryWidget extends Component {

    // FIX-1: template declared as tagged template literal on the class
    static template = xml`
        <div class="o_pharmacy_stock_summary d-flex align-items-center gap-3 py-1 flex-wrap">
            <t t-if="state.loading">
                <span class="text-muted">
                    <i class="fa fa-spinner fa-spin me-1"/>Loading&#8230;
                </span>
            </t>
            <t t-else="">
                <span class="badge bg-secondary fs-6"
                      title="Total physical units in all internal locations">
                    <i class="fa fa-cubes me-1"/>
                    On Hand:&#160;<strong t-esc="state.onHand.toFixed(2)"/>
                </span>
                <span class="badge bg-primary fs-6"
                      title="Units committed to confirmed transfers">
                    <i class="fa fa-lock me-1"/>
                    Reserved:&#160;<strong t-esc="state.reserved.toFixed(2)"/>
                </span>
                <span t-attf-class="badge fs-6 {{ state.available > 0 ? 'bg-success' : 'bg-danger' }}"
                      title="On Hand minus Reserved — usable for new transfers or POS sales">
                    <i class="fa fa-check-circle me-1"/>
                    Available:&#160;<strong t-esc="state.available.toFixed(2)"/>
                </span>
            </t>
        </div>
    `;

    // FIX-4: Odoo 18 OWL 2 static props
    static props = {
        id:         { type: Number, optional: true },
        record:     { type: Object, optional: true },
        // Standard field widget props passed by the view framework
        name:       { type: String, optional: true },
        string:     { type: String, optional: true },
        readonly:   { type: Boolean, optional: true },
        value:      { optional: true },
    };

    setup() {
        this.orm   = useService("orm");
        this.state = useState({ onHand: 0, reserved: 0, available: 0, loading: true });

        onWillStart(() => this._loadData());
    }

    async _loadData() {
        // Resolve product id from the view record context
        const productId =
            this.props.record?.data?.id ||
            this.props.id ||
            null;

        if (!productId) {
            this.state.loading = false;
            return;
        }
        try {
            const [rec] = await this.orm.read(
                "product.product",
                [productId],
                ["qty_available", "pharmacy_reserved_qty", "pharmacy_available_qty"],
            );
            if (rec) {
                this.state.onHand    = rec.qty_available              || 0;
                this.state.reserved  = rec.pharmacy_reserved_qty      || 0;
                this.state.available = rec.pharmacy_available_qty     || 0;
            }
        } catch (err) {
            console.warn("[PharmacyStockSummaryWidget] Failed to load qty data:", err);
        } finally {
            this.state.loading = false;
        }
    }
}

// Register as a field widget usable in views via widget="pharmacy_stock_summary"
registry.category("fields").add("pharmacy_stock_summary", {
    component:   PharmacyStockSummaryWidget,
    displayName: "Pharmacy Stock Summary",
    supportedTypes: ["float", "integer"],
});
