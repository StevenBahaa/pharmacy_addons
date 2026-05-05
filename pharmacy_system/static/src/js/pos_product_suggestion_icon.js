/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { useService } from "@web/core/utils/hooks";
import { ProductSuggestionsPopup } from "./pos_product_suggestions_popup";

console.log("🟢 POS product suggestion icon loaded");

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    openProductSuggestions(ev) {
        if (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }

        const product = this.props.product;

        if (!product || !product.x_has_pos_related_products) {
            return;
        }

        // Resolve Many2many IDs to actual product records from the POS store
        const pos = this.env.services.pos;
        const similarIds = product.x_pos_similar_product_ids || [];
        const complementaryIds = product.x_pos_complementary_product_ids || [];

        const similarProducts = [];
        for (const item of similarIds) {
            const id = typeof item === "object" ? item.id : item;
            const rec = pos.models["product.product"].get(id);
            if (rec) {
                similarProducts.push(rec);
            }
        }

        const complementaryProducts = [];
        for (const item of complementaryIds) {
            const id = typeof item === "object" ? item.id : item;
            const rec = pos.models["product.product"].get(id);
            if (rec) {
                complementaryProducts.push(rec);
            }
        }

        if (!similarProducts.length && !complementaryProducts.length) {
            return;
        }

        this.dialog.add(ProductSuggestionsPopup, {
            title: "Suggested Products",
            currentProduct: product,
            similarProducts: similarProducts,
            complementaryProducts: complementaryProducts,
        });
    },
});