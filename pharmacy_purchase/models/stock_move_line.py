from odoo import models, fields, api, _

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_is_consignment_processed = fields.Boolean(string="Consignment Processed", default=False, copy=False)

    def _action_done(self):
        res = super()._action_done()
        for ml in self:
            if ml.state != 'done' or ml.x_is_consignment_processed:
                continue
                
            picking = ml.picking_id
            if not picking:
                continue

            processed = False
            # 1. Handle Consignment Sale (Outgoing move with vendor owner)
            if picking.picking_type_id.code == 'outgoing' and ml.owner_id:
                ml._update_consignment_sale_qty()
                processed = True
                
                # If it's also a Return to Vendor (supplier location)
                if ml.location_dest_id.usage == 'supplier':
                    ml._update_consignment_return_qty()

            # 2. Handle Consignment Receipt (Incoming from PO)
            if not processed:
                po = ml.move_id.purchase_line_id.order_id or picking.purchase_id
                if po and po.is_consignment and picking.picking_type_id.code == 'incoming':
                    ml._create_or_update_consignment_stock_line()
                    processed = True
            
            if processed:
                ml.x_is_consignment_processed = True
                    
        return res

    def _create_or_update_consignment_stock_line(self):
        self.ensure_one()
        if self.x_is_consignment_processed:
            return
            
        po_line = self.move_id.purchase_line_id
        if not po_line:
            # Fallback to searching PO line
            picking = self.picking_id
            po = picking.purchase_id or self.move_id.purchase_line_id.order_id
            if po:
                po_line = self.env['purchase.order.line'].search([
                    ('order_id', '=', po.id),
                    ('product_id', '=', self.product_id.id)
                ], limit=1)

        if not po_line:
            return

        # Find existing line for this PO line + lot
        cons_line = self.env['pharmacy.consignment.stock.line'].search([
            ('purchase_order_line_id', '=', po_line.id),
            ('lot_id', '=', self.lot_id.id)
        ], limit=1)

        if cons_line:
            cons_line.received_qty += self.quantity
        else:
            self.env['pharmacy.consignment.stock.line'].create({
                'purchase_order_id': po_line.order_id.id,
                'purchase_order_line_id': po_line.id,
                'product_id': self.product_id.id,
                'lot_id': self.lot_id.id,
                'received_qty': self.quantity,
            })
        self.x_is_consignment_processed = True

    def _update_consignment_sale_qty(self):
        self.ensure_one()
        
        # Determine the vendor owner
        vendor_id = self.owner_id.id
        if not vendor_id and self.lot_id:
            # Fallback: Find the vendor from the original consignment tracking of this lot
            tracking_line = self.env['pharmacy.consignment.stock.line'].search([
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id)
            ], limit=1)
            if tracking_line:
                vendor_id = tracking_line.vendor_id.id

        if not vendor_id:
            return

        # Match by product + vendor owner + lot
        # We search for the oldest consignment line that has remaining quantity
        cons_lines = self.env['pharmacy.consignment.stock.line'].search([
            ('product_id', '=', self.product_id.id),
            ('vendor_id', '=', vendor_id),
            ('lot_id', '=', self.lot_id.id),
            ('remaining_qty', '>', 0)
        ], order='id asc')

        qty_to_attribute = self.quantity
        for line in cons_lines:
            if qty_to_attribute <= 0:
                break
            
            attribute_qty = min(qty_to_attribute, line.remaining_qty)
            line.sold_qty += attribute_qty
            qty_to_attribute -= attribute_qty
        
        # If there's still qty_to_attribute > 0, it means we sold more than we tracked as received
        # for this specific lot/owner combination.
        if qty_to_attribute > 0 and cons_lines:
            cons_lines[0].sold_qty += qty_to_attribute

    def _update_consignment_return_qty(self):
        self.ensure_one()
        # Find the consignment line that matches this return
        # Usually a return to vendor is linked to a specific PO via the picking/move
        po_line = self.move_id.purchase_line_id
        
        domain = [
            ('product_id', '=', self.product_id.id),
            ('vendor_id', '=', self.owner_id.id),
            ('lot_id', '=', self.lot_id.id),
        ]
        if po_line:
            domain.append(('purchase_order_line_id', '=', po_line.id))
            
        cons_line = self.env['pharmacy.consignment.stock.line'].search(domain, limit=1, order='id desc')
        
        if cons_line:
            cons_line.returned_qty += self.quantity
