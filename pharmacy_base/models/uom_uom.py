from odoo import api, models
from odoo.osv import expression


class UomUom(models.Model):
    _inherit = "uom.uom"

    @api.model
    def _pharmacy_get_sale_allowed_uom_ids_from_context(self):
        """
        Restrict UoM lookup only when pharmacy sale context is present.
        Returns [package_uom_id, ratio_uom_id] for the current product/template.
        """
        ctx = self.env.context
        product_id = ctx.get("pharmacy_sale_product_id")
        product_tmpl_id = ctx.get("pharmacy_sale_product_tmpl_id")

        tmpl = False
        if product_id:
            product = self.env["product.product"].browse(product_id).exists()
            tmpl = product.product_tmpl_id if product else False
        elif product_tmpl_id:
            tmpl = self.env["product.template"].browse(product_tmpl_id).exists()

        if not tmpl:
            # Fallback when editing an existing sale line record from dialogs/actions.
            if ctx.get("active_model") == "sale.order.line" and ctx.get("active_id"):
                line = self.env["sale.order.line"].browse(ctx["active_id"]).exists()
                tmpl = line.product_id.product_tmpl_id if line and line.product_id else False
                if not tmpl and line:
                    tmpl = line.product_template_id
            if not tmpl:
                return []

        allowed_ids = []
        if tmpl.uom_id:
            allowed_ids.append(tmpl.uom_id.id)
        if tmpl.package_uom_id:
            allowed_ids.append(tmpl.package_uom_id.id)

        # Keep deterministic order, remove duplicates
        return list(dict.fromkeys(allowed_ids))

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = list(domain or [])
        allowed_ids = self._pharmacy_get_sale_allowed_uom_ids_from_context()
        if allowed_ids:
            domain = expression.AND([domain, [("id", "in", allowed_ids)]])

        if name:
            name_domain = [('name', operator, name)]
            domain = expression.AND([domain, name_domain])

        return self._search(domain, limit=limit, order=order)
