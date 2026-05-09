# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Management System',
    'version': '18.0.1.0.0',
    'summary': 'Compatibility bridge for split pharmacy modules',
    'description': 'Compatibility bridge for the split Pharmacy Management System modules.',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',

    'depends': [
        'pharmacy_base',
        'pharmacy_stock_expiry',
        'pharmacy_sales_rules',
        'pharmacy_purchase',
        'pharmacy_inventory_ops',
        'pharmacy_pos',
        'pharmacy_reports',
        'pharmacy_stock_reservation',
    ],

    'data': [
    ],

    'assets': {
    },
    'installable': True,
    'application': False,
}
