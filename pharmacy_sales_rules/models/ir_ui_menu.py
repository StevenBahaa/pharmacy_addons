from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        menu_ids = super()._visible_menu_ids(debug=debug)

        commission_menu = self.env.ref(
            'pharmacy_sales_rules.menu_sale_commission_summary',
            raise_if_not_found=False
        )

        if not commission_menu:
            return menu_ids

        if commission_menu.id in menu_ids and not self.env.user._has_commission_menu_access():
            menu_ids.discard(commission_menu.id)

        return menu_ids
