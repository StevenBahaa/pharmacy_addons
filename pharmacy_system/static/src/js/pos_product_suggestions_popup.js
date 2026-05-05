/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ScheduledMedicineWarningPopup } from "./pos_scheduled_medicine_warning_popup";

export class ProductSuggestionsPopup extends Component {
    static template = "pharmacy_system.ProductSuggestionsPopup";
    static components = { Dialog };

    static props = {
        title: { type: String, optional: true },
        currentProduct: { type: Object, optional: true },
        similarProducts: { type: Array, optional: true },
        complementaryProducts: { type: Array, optional: true },
        close: Function,
    };

    async _confirmScheduledProduct(product, body) {
        if (!product || !product.x_is_scheduled) {
            return true;
        }

        const scheduleLabelMap = {
            schedule_1: "Schedule I",
            schedule_2: "Schedule II",
            schedule_3: "Schedule III",
            schedule_4: "Schedule IV",
            schedule_5: "Schedule V",
        };

        const scheduleName =
            scheduleLabelMap[product.x_schedule_level] || "Not defined";

        return await new Promise((resolve) => {
            this.env.services.dialog.add(ScheduledMedicineWarningPopup, {
                title: "Scheduled Medicine Warning",
                body: body || "This product is a controlled substance. Do you want to continue?",
                scheduleName: scheduleName,
                confirmText: "Yes, Continue",
                cancelText: "Cancel",
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
    }

    async addComplementaryProduct(product) {
        if (!product) {
            return;
        }

        const confirmed = await this._confirmScheduledProduct(
            product,
            "This suggested product is a controlled substance. Do you want to add it?"
        );

        if (!confirmed) {
            return;
        }

        const pos = this.env.services.pos;
        await pos.addLineToCurrentOrder(
            { product_id: product },
            {}
        );

        this.close();
    }

    async replaceWithSimilarProduct(product) {
        if (!product) {
            return;
        }

        const confirmed = await this._confirmScheduledProduct(
            product,
            "This alternative product is a controlled substance. Do you want to replace with it?"
        );

        if (!confirmed) {
            return;
        }

        const pos = this.env.services.pos;
        const order = pos.get_order();

        if (!order) {
            console.warn("No current POS order found.");
            return;
        }

        const currentProduct = this.props.currentProduct;

        if (currentProduct) {
            const lineToRemove = order.lines.find(
                (line) => line.product_id && line.product_id.id === currentProduct.id
            );

            if (lineToRemove) {
                order.removeOrderline(lineToRemove);
            }
        }

        await pos.addLineToCurrentOrder(
            { product_id: product },
            {}
        );

        this.close();
    }

    close() {
        this.props.close();
    }
}