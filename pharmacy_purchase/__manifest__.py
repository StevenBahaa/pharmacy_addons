# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Purchase',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy purchase and receipt enhancements',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': ['pharmacy_base', 'pharmacy_stock_expiry', 'purchase', 'stock', 'account', 'product_expiry'],
    'data': [
        'views/purchase_order_line_uom_views.xml',
        'views/purchase_order_consignment_views.xml',
        'views/product_purchase_views.xml',
    ],
    'installable': True,
    'application': False,
}
