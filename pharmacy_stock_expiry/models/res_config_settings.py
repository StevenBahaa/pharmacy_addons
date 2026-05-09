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
    notification_recipients = fields.Many2many(
        'res.users', 
        string="Notification Recipients",
        help="Inventory Managers who will receive expiry notifications"
    )

    def set_values(self):
        super().set_values()
        # Store Many2many IDs as a comma-separated string in ir.config_parameter
        ids_str = ",".join(map(str, self.notification_recipients.ids))
        self.env['ir.config_parameter'].sudo().set_param('pharmacy_expiry.notification_recipients', ids_str)

    def get_values(self):
        res = super().get_values()
        ids_str = self.env['ir.config_parameter'].sudo().get_param('pharmacy_expiry.notification_recipients')
        if ids_str:
            ids = [int(i) for i in ids_str.split(',') if i.isdigit()]
            res.update(notification_recipients=[(6, 0, ids)])
        return res
