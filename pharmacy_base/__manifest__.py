# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Base',
    'version': '18.0.1.0.0',
    'summary': 'Shared pharmacy product, security, and UoM foundations',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/package_uom_data.xml',
        'data/ir_sequence_product_data.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
}
