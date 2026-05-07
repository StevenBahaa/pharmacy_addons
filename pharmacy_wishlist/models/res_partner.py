# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    pharmacy_customer_code = fields.Char(string='Pharmacy Customer Code', copy=False, index=True)

    _sql_constraints = [
        ('pharmacy_customer_code_unique', 'unique(pharmacy_customer_code)', 'The Pharmacy Customer Code must be unique!')
    ]
