# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy POS',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy POS warnings and product suggestions',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': [
        'pharmacy_base',
        'point_of_sale',
        'pharmacy_stock_expiry',
        'pharmacy_sales_rules',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pharmacy_pos/static/src/js/pos_scheduled_medicine_warning_popup.js',
            'pharmacy_pos/static/src/js/pos_scheduled_medicine_popup.js',
            'pharmacy_pos/static/src/js/pos_product_suggestions_popup.js',
            'pharmacy_pos/static/src/js/pos_product_suggestion_icon.js',
            'pharmacy_pos/static/src/xml/scheduled_medicine_warning_popup.xml',
            'pharmacy_pos/static/src/xml/pos_product_suggestions_popup.xml',
            'pharmacy_pos/static/src/xml/pos_product_suggestion_icon.xml',
            'pharmacy_pos/static/src/css/scheduled_medicine_warning_popup.css',
            'pharmacy_pos/static/src/css/pos_product_suggestion_icon.css',
        ],
    },
    'installable': True,
    'application': False,
}
