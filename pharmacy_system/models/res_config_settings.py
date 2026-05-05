from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_product_commission = fields.Boolean(
        string='Enable Product Commissions',
        default=True,
        help='When enabled, commission amounts will be calculated on sale orders.'
    )

    def write(self, vals):
        res = super().write(vals)
        if 'enable_product_commission' in vals:
            self.env['ir.ui.menu'].clear_caches()
        return res
    

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_product_commission = fields.Boolean(
        related='company_id.enable_product_commission',
        readonly=False,
        string='Enable Product Commissions',
        help='When enabled, commission amounts will be calculated on sale orders.'
    )

    def set_values(self):
        res = super().set_values()
        self.env['ir.ui.menu'].clear_caches()
        return res

    near_expiry_limit = fields.Integer(
        string="Near Expiry Warning (Days)",
        config_parameter='pharmacy_mgmt.near_expiry_limit',
        default=30,
        help="Default days to show orange warning (Level 1)"
    )
    
    
    critical_expiry_limit = fields.Integer(
        string="Critical Expiry Alert (Days)",
        config_parameter='pharmacy_mgmt.critical_expiry_limit',
        default=7,
        help="Default days to show red alert and POS icon (Level 2)"
    )