/** @odoo-module **/
/**
 * Pharmacy Count — Barcode scan handler
 *
 * Listens to the barcode input field on the pharmacy.count form view.
 * On scan/enter: calls find_line_by_barcode on the server, then scrolls
 * to and highlights the matching line row in the One2many list.
 */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

// Only patch when we are on the pharmacy.count form
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this._pharmacyBarcodeHandler = null;

        onMounted(() => {
            if (this.props.resModel === "pharmacy.count") {
                this._attachBarcodeListener();
            }
        });

        onWillUnmount(() => {
            this._detachBarcodeListener();
        });
    },

    _attachBarcodeListener() {
        const input = document.querySelector(".pharmacy-barcode-input");
        const btn = document.querySelector(".pharmacy-barcode-btn");
        if (!input) return;

        const handler = async (e) => {
            if (e.type === "click" || (e.type === "keydown" && e.key === "Enter")) {
                e.preventDefault();
                const barcode = input.value.trim();
                if (!barcode) return;
                await this._handleBarcode(barcode);
                input.value = "";
                input.focus();
            }
        };

        input.addEventListener("keydown", handler);
        if (btn) btn.addEventListener("click", handler);
        this._pharmacyBarcodeHandler = { input, btn, handler };
    },

    _detachBarcodeListener() {
        if (!this._pharmacyBarcodeHandler) return;
        const { input, btn, handler } = this._pharmacyBarcodeHandler;
        input.removeEventListener("keydown", handler);
        if (btn) btn.removeEventListener("click", handler);
        this._pharmacyBarcodeHandler = null;
    },

    async _handleBarcode(barcode) {
        const recordId = this.model.root.resId;
        if (!recordId) {
            this.notification.add("Save the record before scanning.", {
                type: "warning",
            });
            return;
        }

        const result = await this.env.services.rpc(
            "/web/dataset/call_kw",
            {
                model: "pharmacy.count",
                method: "find_line_by_barcode",
                args: [[recordId], barcode],
                kwargs: {},
            }
        );

        if (result.error) {
            this.notification.add(result.error, { type: "danger" });
            return;
        }

        // Highlight the row in the One2many list
        this._highlightLine(result.line_id, result.product_name);
    },

    _highlightLine(lineId, productName) {
        // Remove previous highlights
        document.querySelectorAll(".pharmacy-highlighted").forEach((el) => {
            el.classList.remove("pharmacy-highlighted");
        });

        // Find the row whose data-id matches lineId
        const rows = document.querySelectorAll(
            ".o_field_one2many .o_data_row"
        );
        for (const row of rows) {
            if (row.dataset.id == lineId) {
                row.classList.add("pharmacy-highlighted");
                row.scrollIntoView({ behavior: "smooth", block: "center" });
                this.notification.add(
                    `✓ ${productName} — enter counted quantity`,
                    { type: "success", sticky: false }
                );
                // Remove highlight after 4 s
                setTimeout(() => row.classList.remove("pharmacy-highlighted"), 4000);
                return;
            }
        }

        this.notification.add(
            `Product "${productName}" found but row not visible.`,
            { type: "warning" }
        );
    },
});
