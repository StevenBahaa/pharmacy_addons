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
        'security/ir.model.access.csv',
        'views/purchase_order_line_uom_views.xml',
        'views/product_purchase_views.xml',
        'views/purchase_order_consignment_views.xml',
        'views/stock_move_line_views.xml',
        'views/product_discount_history_views.xml',
        'views/purchase_order_tracking_views.xml',
        'views/purchase_order_tracking_menus.xml',
        'wizard/consignment_track_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
