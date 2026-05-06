/** @odoo-module **/

import { Component } from "@odoo/owl";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { WishlistDialog } from "./wishlist_dialog";

export class WishlistButton extends Component {
    static template = "pharmacy_wishlist.WishlistButton";

    setup() {
        this.pos = useService("pos");
        this.dialog = useService("dialog");
    }

    get isVisible() {
        return this.pos.user && this.pos.user.wishlist_permission;
    }

    onClick() {
        const order = this.pos.get_order();
        const partner = order ? order.get_partner() : null;
        
        this.dialog.add(WishlistDialog, {
            title: "Add to Wishlist",
            customer_name: partner ? partner.name : "",
            customer_phone: partner ? (partner.phone || partner.mobile || "") : "",
            customer_code: partner ? (partner.ref || "") : "",
            confirm: async (customer_data, lines) => {
                try {
                    // Create a wishlist record for each product line
                    const promises = lines.map(line => {
                        return this.pos.data.create("pharmacy.wishlist", [{
                            customer_name: customer_data.customer_name,
                            customer_phone: customer_data.customer_phone,
                            product_id: parseInt(line.product_id),
                            quantity: parseFloat(line.quantity) || 1,
                            note: line.note,
                            shop_name: this.pos.config.name,
                        }]);
                    });
                    
                    await Promise.all(promises);
                    
                    this.env.services.notification.add("Added to Wishlist successfully.", {
                        type: "success",
                    });
                } catch (error) {
                    console.error("Wishlist Error:", error);
                    this.env.services.notification.add("Failed to add to wishlist.", {
                        type: "danger",
                    });
                }
            },
        });
    }
}

patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        WishlistButton,
    },
});
