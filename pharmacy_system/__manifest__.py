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
        'pharmacy_wishlist',
        'pharmacy_reports',
        'pharmacy_stock_reservation',
        'pharmacy_inventory_advanced',
        'sale_stock_restrict',
    ],

    'data': [
        'views/stock_picking_views.xml',
        'views/stock_quant_view.xml',
        'views/stock_lot_views.xml',
        'views/expired_medicines_views.xml',
        'views/stock_location_view.xml',
    ],

    'assets': {
    },
    'installable': True,
    'application': False,
}
