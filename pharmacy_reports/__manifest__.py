# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Reports',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy QWeb reports and XLSX exports',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': [
        'pharmacy_base',
        'pharmacy_stock_expiry',
        'pharmacy_sales_rules',
        'pharmacy_inventory_ops',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/expired_medicines_report_wizard_view.xml',
        'wizard/expired_export_wizard_view.xml',
        'views/expired_medicines_report_actions.xml',
        'report/expired_medicines_report_template.xml',
    ],
    'installable': True,
    'application': False,
}
