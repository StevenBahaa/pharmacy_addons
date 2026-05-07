# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    wishlist_permission = fields.Boolean(
        string='Can Manage POS Wishlist',
        default=False,
        help='If checked, the user will see the Wishlist button in the POS.'
    )

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if 'wishlist_permission' not in fields_list:
            fields_list.append('wishlist_permission')
        return fields_list

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append('pharmacy_customer_code')
        return fields_list
