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
        // Show only if the logged-in user has the wishlist_permission flag
        const user = this.pos.user;
        return user && user.wishlist_permission;
    }

    onClick() {
        const order = this.pos.get_order();
        const partner = order ? order.get_partner() : null;
        const phone = partner ? (partner.phone || partner.mobile || "") : "";

        this.dialog.add(WishlistDialog, {
            title: "Add to Wishlist",
            customer_phone: phone,
            confirm: async (vals) => {
                try {
                    await this.pos.data.create("pharmacy.wishlist", [{
                        ...vals,
                        shop_name: this.pos.config.name,
                    }]);
                    this.env.services.notification.add("Product added to wishlist!", {
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

// Register WishlistButton into ControlButtons components map
patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        WishlistButton,
    },
});
