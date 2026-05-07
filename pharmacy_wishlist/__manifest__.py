# -*- coding: utf-8 -*-
{
    'name': 'Pharmacy Wishlist',
    'version': '18.0.1.0.0',
    'summary': 'Bridges POS, Inventory, and CRM for customer product requests',
    'description': """
        Pharmacy Wishlist (SC5-UC-01)
        - POS button to record product requests
        - Automatic partner creation based on phone
        - Inventory triggers to alert when wishlist products arrive
        - CRM dashboard for follow-up calls
    """,
    'author': 'Antigravity',
    'category': 'Healthcare/Pharmacy',
    'license': 'LGPL-3',
    'depends': [
        'pharmacy_base',
        'point_of_sale',
        'stock',
        'crm',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/pharmacy_wishlist_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pharmacy_wishlist/static/src/js/wishlist_button.js',
            'pharmacy_wishlist/static/src/js/wishlist_dialog.js',
            'pharmacy_wishlist/static/src/xml/wishlist_button.xml',
            'pharmacy_wishlist/static/src/xml/wishlist_dialog.xml',
            'pharmacy_wishlist/static/src/css/wishlist.css',
        ],
    },
    'installable': True,
    'application': True,
}
