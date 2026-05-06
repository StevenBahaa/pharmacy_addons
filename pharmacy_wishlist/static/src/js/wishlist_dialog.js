/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class WishlistDialog extends Component {
    static template = "pharmacy_wishlist.WishlistDialog";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        customer_phone: { type: String, optional: true },
        confirm: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.pos = useService("pos");
        this.notification = useService("notification");
        this.state = useState({
            customer_phone: this.props.customer_phone || "",
            product_id: "",
            quantity: 1,
            note: "",
        });
    }

    get products() {
        // Compatible with Odoo 18 POS model store
        return this.pos.models["product.product"].getAll().filter((p) => p.available_in_pos);
    }

    async onConfirm() {
        if (!this.state.customer_phone) {
            this.notification.add("Customer phone is required.", { type: "danger" });
            return;
        }
        if (!this.state.product_id) {
            this.notification.add("Product is required.", { type: "danger" });
            return;
        }

        await this.props.confirm({
            customer_phone: this.state.customer_phone,
            product_id: parseInt(this.state.product_id),
            quantity: parseFloat(this.state.quantity) || 1,
            note: this.state.note,
        });
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}
