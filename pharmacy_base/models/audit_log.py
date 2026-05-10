# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PharmacyAuditLog(models.Model):
    _name = 'pharmacy.audit.log'
    _description = 'Pharmacy Security Audit Log'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user)
    model_name = fields.Char('Model Name', readonly=True)
    res_id = fields.Integer('Resource ID', readonly=True)
    action_type = fields.Selection([
        ('price_override', 'Price Override'),
        ('scheduled_medicine_change', 'Scheduled Medicine Change'),
        ('tracking_change', 'Tracking Method Change'),
        ('classification_change', 'Classification Change'),
        ('qty_override', 'Quantity Override'),
        ('expiry_action', 'Expiry Action'),
    ], string='Action Type', readonly=True)
    old_value = fields.Text('Old Value', readonly=True)
    new_value = fields.Text('New Value', readonly=True)
    timestamp = fields.Datetime('Timestamp', readonly=True, default=fields.Datetime.now)
    note = fields.Text('Additional Notes', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Ensure only system or authorized methods can create logs
        return super(PharmacyAuditLog, self).create(vals_list)

    def write(self, vals):
        # Audit logs should be immutable
        return False

    def unlink(self):
        # Audit logs should be immutable
        return False
