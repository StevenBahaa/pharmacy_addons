from odoo import models, fields , api 


class PharmacyShortageLine(models.Model):
    _name = 'pharmacy.shortage.line'
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
        readonly=True
    )

    max_qty = fields.Float(
        string='Max Qty',
        readonly=True
    )

    onhand_qty = fields.Float(
        string='Onhand Qty',
        readonly=True
    )

    reserved_qty = fields.Float(
        string='Reserved Qty',
        readonly=True
    )

    available_qty = fields.Float(
        string='Available Qty',
        readonly=True
    )

    incoming_qty = fields.Float(
        string='Incoming Qty',
        readonly=True
    )

    shortage_qty = fields.Float(
        string='Shortage Qty',
        readonly=True
    )

    urgency_level = fields.Selection([
        ('critical', 'Critical (Out of Stock)'),
        ('warning', 'Warning (Low Stock)'),
        ('normal', 'Normal'),
    ], string='Urgency', compute='_compute_urgency_level', store=True)

    @api.depends('available_qty', 'min_qty')
    def _compute_urgency_level(self):
        for line in self:
            if line.available_qty <= 0:
                line.urgency_level = 'critical'
            elif line.available_qty < (line.min_qty * 0.5):
                line.urgency_level = 'warning'
            else:
                line.urgency_level = 'normal'

    _sql_constraints = [
        ("unique_product_location_warehouse",
         "unique(product_id, location_id, warehouse_id)",
         "Duplicate shortage line!")
    ]

    def _get_onhand_qty(self, product, location):
        Quant = self.env["stock.quant"]

        groups = Quant.read_group(
            [
                ("product_id", "=", product.id),
                ("location_id", "child_of", location.id),
                
            ],
            ["quantity:sum"],
            []
        )

        return groups[0]["quantity"] if groups else 0.0

    def _get_reserved_qty(self, product, location):
        groups = self.env["stock.quant"].read_group(
            [
                ("product_id", "=", product.id),
                ("location_id", "child_of", location.id),
            ],
            ["reserved_quantity:sum"],
            []
        )

        return groups[0]["reserved_quantity"] if groups else 0.0

    def _get_incoming_qty(self, product, location):
        Move = self.env["stock.move"]

        groups = Move.read_group(
            [
                ("product_id", "=", product.id),
                ("location_dest_id", "child_of", location.id),
                ("purchase_line_id", "!=", False),
                ("state", "not in", ["done", "cancel"]),
            ],
            ["product_uom_qty:sum"],
            []
        )

        return groups[0]["product_uom_qty"] if groups else 0.0

    def action_refresh_shortage_lines(self):
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        Shortage = self.env["pharmacy.shortage.line"]

        orderpoints = Orderpoint.search([])

        for op in orderpoints:
            onhand_qty = self._get_onhand_qty(op.product_id, op.location_id)
            reserved_qty = self._get_reserved_qty(op.product_id, op.location_id)
            available_qty = onhand_qty - reserved_qty
            shortage_qty = op.product_min_qty - available_qty
            incoming_qty = self._get_incoming_qty(op.product_id, op.location_id)

            existing = Shortage.search([
                    ("product_id", "=", op.product_id.id),
                    ("location_id", "=", op.location_id.id),
                    ("warehouse_id", "=", op.warehouse_id.id)
                ], limit=1)

            if available_qty < op.product_min_qty:
                vals = {
                    "product_id": op.product_id.id,
                    "location_id": op.location_id.id,
                    "warehouse_id": op.warehouse_id.id,
                    "min_qty": op.product_min_qty,
                    "max_qty": op.product_max_qty,
                    "onhand_qty": onhand_qty,
                    "reserved_qty": reserved_qty,
                    "available_qty": available_qty,
                    "shortage_qty": shortage_qty,
                    "incoming_qty": incoming_qty
                }
                if existing:
                    existing.write(vals)
                else:
                    Shortage.create(vals)
        
            else:
                if existing:
                    existing.unlink()
        
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_create_rfq(self):
        self.ensure_one()

        qty = self.shortage_qty

        return {
            "type": "ir.actions.act_window",
            "name": "Create RFQ",
            "res_model": "purchase.order",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_partner_id": self.product_id.seller_ids[:1].partner_id.id,
                "default_order_line": [
                    (0, 0, {
                        "product_id": self.product_id.id,
                        "product_qty": qty,
                        "product_uom": self.product_id.uom_po_id.id or self.product_id.uom_id.id,
                        "name": self.product_id.display_name,
                        "date_planned": fields.Datetime.now(),
                    })
                ]
            },
        }


    

    

    