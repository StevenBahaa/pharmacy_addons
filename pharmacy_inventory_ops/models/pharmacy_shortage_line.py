from odoo import models, fields , api 


class PharmacyShortageLine(models.Model):
    _inherit = 'pharmacy.shortage.line'
    _description = "Pharmacy Shortage Line"

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True
    )

    min_qty = fields.Float(
        string='Min Qty',
        required=True
    )

    max_qty = fields.Float(
        string='Max Qty',
        required=True
    )

    onhand_qty = fields.Float(
        string='Onhand Qty',
        required=True
    )

    reserved_qty = fields.Float(
        string='Reserved Qty',
        required=True
    )

    available_qty = fields.Float(
        string='Available Qty',
        required=True
    )

    incoming_qty = fields.Float(
        string='Incoming Qty',
        required=True
    )

    shortage_qty = fields.Float(
        string='Shortage Qty',
        required=True
    )

    _sql_constraints = [
        ("unique_product_location",
         "unique(product_id, location_id)",
         "Duplicate shortage line!")
    ]

    

    

    