# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Inventory Operations',
    'version': '18.0.1.0.0',
    'summary': 'Pharmacy inventory operations, low stock logs, and AVCO defaults',
    'description': """
        Extends Odoo Inventory Adjustment with:
        - Daily spot-check with mandatory reason field
        - Full periodic count wizard with warehouse/category/location filters
        - Counted / Not Counted status tracking per line
        - Barcode scanning support
        - Discrepancy report (PDF + Excel)
        - Count summary dashboard
        - Pharmacy inventory operations, low stock logs, and AVCO defaults
    """,
    'author': 'Steven Bahaa',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': ['pharmacy_base', 'stock', 'purchase', 'stock_account', 'product', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/pharmacy_security_rules.xml',
        'data/product_category_data.xml',
        'data/sequence.xml',
        'data/ir_cron.xml',
        'views/pharmacy_shortage_line_view.xml',
        'views/pharmacy_count_views.xml',
        'views/pharmacy_count_line_views.xml',
        'wizard/periodic_count_wizard_views.xml',
        'wizard/mark_not_found_wizard_views.xml',
        'report/pharmacy_count_report_template.xml',
        'report/pharmacy_count_report_action.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pharmacy_inventory_ops/static/src/css/pharmacy_count.css',
            'pharmacy_inventory_ops/static/src/xml/barcode_highlight.xml',
            'pharmacy_inventory_ops/static/src/js/barcode_count_handler.js',
        ],
        'web.assets_tests': [
            'pharmacy_inventory_ops/static/src/js/tours/pharmacy_count_tours.js',
        ],
    },
    'post_init_hook': '_post_init_force_avco',
    'installable': True,
    'application': False,
}
