{
    'name': 'Pharmacy Reports & Exports',
    'version': '18.0.1.0.0',
    'category': 'Pharmacy/Reports',
    'summary': 'Unified reporting and Excel export system for Pharmacy Management.',
    'author': 'Senior ERP Developer',
    'license': 'LGPL-3',
    'depends': [
        'pharmacy_inventory_ops',
        'report_xlsx',
        'pharmacy_base'
    ],
    'data': [
        'report/pharmacy_shortage_report.xml',
        'views/pharmacy_shortage_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
