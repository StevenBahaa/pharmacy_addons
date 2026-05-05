from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_manufacturer = fields.Boolean(string='Is Manufacturer')
