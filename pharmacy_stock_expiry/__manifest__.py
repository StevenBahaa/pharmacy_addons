# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Stock Expiry',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy lot expiry, expired locations, and expiry workflows',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': ['pharmacy_base', 'stock', 'product_expiry', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/expiry_cron.xml',
        'wizard/expired_transfer_wizard_view.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_view.xml',
        'views/stock_location_view.xml',
        'views/res_config_settings_views.xml',
        'views/product_expiry_views.xml',
        'views/expired_medicines_views.xml',
    ],
    'installable': True,
    'application': False,
}
