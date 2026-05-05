from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    near_expiry_limit = fields.Integer(
        string="Near Expiry Warning (Days)",
        config_parameter='pharmacy_mgmt.near_expiry_limit',
        default=30,
        help="Default days to show orange warning (Level 1)",
    )
    critical_expiry_limit = fields.Integer(
        string="Critical Expiry Alert (Days)",
        config_parameter='pharmacy_mgmt.critical_expiry_limit',
        default=7,
        help="Default days to show red alert and POS icon (Level 2)",
    )
