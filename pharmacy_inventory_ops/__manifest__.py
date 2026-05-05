# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Inventory Operations',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy inventory operations, low stock logs, and AVCO defaults',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': ['pharmacy_base', 'stock', 'purchase', 'stock_account'],
    'data': [
        'data/product_category_data.xml',
    ],
    'post_init_hook': '_post_init_force_avco',
    'installable': True,
    'application': False,
}
