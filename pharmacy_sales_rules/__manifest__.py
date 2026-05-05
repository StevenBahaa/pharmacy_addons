# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Sales Rules',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy sales restrictions, low stock warnings, and commissions',
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': ['pharmacy_base', 'pharmacy_stock_expiry', 'sale_management', 'sale_stock', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_commission_data.xml',
        'wizard/bulk_price_update_view.xml',
        'wizard/low_stock_warning_wizard_view.xml',
        'wizard/sale_order_suggested_products_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/commission_report_views.xml',
        'views/product_pricing_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pharmacy_sales_rules/static/src/js/sale_product_suggestion_widget.js',
            'pharmacy_sales_rules/static/src/css/sale_suggestion_icon.css',
        ],
    },
    'installable': True,
    'application': False,
}
