/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ScheduledMedicineWarningPopup } from "./pos_scheduled_medicine_warning_popup";

console.log("🟢 Scheduled medicine POS patch loaded");

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {

        if (product && product.x_is_scheduled) {
            const scheduleLabelMap = {
                schedule_1: "Schedule I",
                schedule_2: "Schedule II",
                schedule_3: "Schedule III",
                schedule_4: "Schedule IV",
                schedule_5: "Schedule V",
            };

            const scheduleName =
                scheduleLabelMap[product.x_schedule_level] || "Not defined";

            const confirmed = await new Promise((resolve) => {
                this.dialog.add(ScheduledMedicineWarningPopup, {
                    title: "Scheduled Medicine Warning",
                    body: "This product is a controlled substance. Do you want to continue?",
                    scheduleName: scheduleName,
                    confirmText: "Yes, Add Product",
                    cancelText: "Cancel",
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });

            if (!confirmed) {
                return;
            }
        }

        return await super.addProductToOrder(product);
    },
});