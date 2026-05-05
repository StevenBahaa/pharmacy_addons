# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from datetime import date
from odoo import models, fields , api , _ 


class ExpiredMedicinesReportWizard(models.TransientModel):
    _name = 'expired.medicines.report.wizard'
    _description = 'Expired Medicines Report Wizard'

    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ],string='Month',required=True,default=str(date.today().month))

    year = fields.Char(
        string='Year',
        default=lambda self: str(date.today().year),
        required=True,
    )
    
    location_ids = fields.Many2many(
        'stock.location',
        string='Expired Locations (Branches)',
        domain=[('usage', '=', 'expired')],
        required=True,
    )

    def action_print_pdf(self):
        return self.env.ref(
            'pharmacy_reports.action_report_expired_medicines'
        ).report_action(self)
