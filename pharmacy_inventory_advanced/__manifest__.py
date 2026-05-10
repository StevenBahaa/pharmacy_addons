{
    'name': 'Pharmacy Advanced Inventory',
    'version': '18.0.1.0',
    'category': 'Inventory',
    'summary': 'Bulk Scrap (SC4-UC-03) and Consumption Forecast (SC4-UC-04)',
    'description': """
        Advanced Inventory features for Pharmacy:
        - Bulk Scraping of multiple products with mandatory reason.
        - Consumption forecasting based on 3-month rolling average.
        - Color-coded stock coverage alerts.
    """,
    'author': 'Mohamed Atef',
    'depends': ['stock', 'purchase', 'purchase_requisition'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/bulk_scrap_views.xml',
        'views/consumption_forecast_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}