/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class WishlistDialog extends Component {
    static template = "pharmacy_wishlist.WishlistDialog";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        customer_name: { type: String, optional: true },
        customer_phone: { type: String, optional: true },
        customer_code: { type: String, optional: true },
        confirm: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.pos = useService("pos");
        this.notification = useService("notification");
        this.state = useState({
            customer_name: this.props.customer_name || "",
            customer_phone: this.props.customer_phone || "",
            lines: [this.createEmptyLine()],
        });
    }

    createEmptyLine() {
        return {
            product_id: "",
            quantity: 1,
            note: "",
        };
    }

    get products() {
        return this.pos.models["product.product"].getAll().filter((p) => {
            // Filter products that are available in POS and have 0 or less stock
            return p.available_in_pos && (p.qty_available <= 0);
        });
    }

    addLine() {
        this.state.lines.push(this.createEmptyLine());
    }

    removeLine(index) {
        if (this.state.lines.length > 1) {
            this.state.lines.splice(index, 1);
        } else {
            this.state.lines[0] = this.createEmptyLine();
        }
    }

    async onConfirm() {
        if (!this.state.customer_name) {
            this.notification.add("Customer name is required.", { type: "danger" });
            return;
        }
        if (!this.state.customer_phone) {
            this.notification.add("Customer phone is required.", { type: "danger" });
            return;
        }

        const validLines = this.state.lines.filter(l => l.product_id);
        if (validLines.length === 0) {
            this.notification.add("At least one product must be selected.", { type: "danger" });
            return;
        }

        // Final validation for each product's stock
        for (const line of validLines) {
            const product = this.pos.models["product.product"].get(parseInt(line.product_id));
            if (product && product.qty_available > 0) {
                this.notification.add(`Product ${product.display_name} is still in stock (${product.qty_available}). Please sell it instead.`, { type: "warning" });
                return;
            }
        }

        await this.props.confirm(
            {
                customer_name: this.state.customer_name,
                customer_phone: this.state.customer_phone,
            },
            validLines
        );
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}
