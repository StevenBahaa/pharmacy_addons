# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    wishlist_permission = fields.Boolean(
        string='Can Manage POS Wishlist',
        compute='_compute_wishlist_permission',
        help='Automatically enabled for Cashiers and Pharmacy Managers.'
    )

    def _compute_wishlist_permission(self):
        group_cashier = 'pharmacy_base.group_cashier'
        group_manager = 'pharmacy_base.group_pharmacy_manager'
        for user in self:
            user.wishlist_permission = user.has_group(group_cashier) or user.has_group(group_manager)

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if 'wishlist_permission' not in fields_list:
            fields_list.append('wishlist_permission')
        return fields_list
