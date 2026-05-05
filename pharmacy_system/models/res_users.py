from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _has_commission_menu_access(self):
        self.ensure_one()
        is_manager = (
            self.has_group('pharmacy_system.group_pharmacy_manager')
            or self.has_group('pharmacy_system.group_pricing_manager')
        )
        return is_manager and bool(self.company_id.enable_product_commission)