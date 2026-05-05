/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";

export class ScheduledMedicineWarningPopup extends AbstractAwaitablePopup {
    static template = "pharmacy_system.ScheduledMedicineWarningPopup";
    static defaultProps = {
        confirmText: _t("Yes, Add Product"),
        cancelText: _t("Cancel"),
        title: _t("Scheduled Medicine Warning"),
        body: "",
        scheduleName: "",   };

    async confirm() {
        this.props.close({ confirmed: true, payload: null });
    }

    async cancel() {
        this.props.close({ confirmed: false, payload: null });
    }
}