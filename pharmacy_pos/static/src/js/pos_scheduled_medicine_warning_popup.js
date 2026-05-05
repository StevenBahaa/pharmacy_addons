/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class ScheduledMedicineWarningPopup extends Component {
    static template = "pharmacy_pos.ScheduledMedicineWarningPopup";
    static components = { Dialog };

    static props = {
        close: Function,
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        scheduleName: { type: String, optional: true },
        confirmText: { type: String, optional: true },
        cancelText: { type: String, optional: true },
        confirm: { type: Function, optional: true },
        cancel: { type: Function, optional: true },
    };

    static defaultProps = {
        title: _t("Scheduled Medicine Warning"),
        body: "",
        scheduleName: "",
        confirmText: _t("Yes, Add Product"),
        cancelText: _t("Cancel"),
    };

    onConfirm() {
        if (this.props.confirm) {
            this.props.confirm();
        }
        this.props.close();
    }

    onCancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }
}
