from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_product_commission = fields.Boolean(
        string='Enable Product Commissions',
        default=True,
        help='When enabled, commission amounts will be calculated on sale orders.',
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
        help='When enabled, commission amounts will be calculated on sale orders.',
    )

    def set_values(self):
        res = super().set_values()
        self.env['ir.ui.menu'].clear_caches()
        return res
