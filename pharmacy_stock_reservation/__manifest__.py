{
    'name': 'Pharmacy Stock Reservation & Transfer Locking',
    'version': '18.0.1.0.0',
    'summary': 'Lock inventory committed to transfers — prevents double-shipping in multi-branch pharmacy networks',
    'description': """
        INV-UC-04 — Stock Reservation & Transfer Locking
        =================================================
        Features:
        - Automatic reservation when transfer is confirmed (out of Draft)
        - On Hand / Reserved / Available computed fields on product & stock quant
        - Blocks transfers and POS sales that exceed available (unreserved) qty
        - Real-time release on cancellation or revert-to-draft
        - Force Unreserve button with mandatory audit log entry
        - Reserved Stock filter on stock quants report
        - Auto-Transfer screen shows reserved alongside on-hand quantities
        - Transfer confirmation pop-up with Available / Reserved / status per line
    """,
    'author': 'Custom Development',
    'category': 'Inventory/Inventory',
    'depends': [
        'pharmacy_base',
        'stock',
        'purchase',
        'sale_stock',
        'point_of_sale',
    ],
    'data': [
        'security/pharmacy_reservation_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/stock_quant_views.xml',
        'views/stock_picking_views.xml',
        'views/product_views.xml',
        'views/reservation_log_views.xml',
        'views/menu_views.xml',
        'wizard/force_unreserve_wizard_views.xml',
        'wizard/transfer_confirm_wizard_views.xml',
        'report/reservation_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pharmacy_stock_reservation/static/src/css/reservation.css',
            'pharmacy_stock_reservation/static/src/js/reservation_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
