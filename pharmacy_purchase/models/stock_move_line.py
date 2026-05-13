from odoo import models, fields, api, _

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_is_consignment_processed = fields.Boolean(string="Consignment Processed", default=False, copy=False)

    def _action_done(self):
        res = super()._action_done()
        import logging
        _logger = logging.getLogger(__name__)
        for ml in self:
            _logger.info("StockMoveLine _action_done: ml=%s, state=%s, processed=%s, picking=%s", ml.id, ml.state, ml.x_is_consignment_processed, ml.picking_id.id if ml.picking_id else None)
            if ml.x_is_consignment_processed:
                continue
                
            picking = ml.picking_id
            if not picking:
                _logger.info("Skipping ml=%s because no picking", ml.id)
                continue

            processed = False
            
            _logger.info("picking code: %s, location_dest_usage: %s", picking.picking_type_id.code, ml.location_dest_id.usage)
            # 1. Consignment Outgoing Moves
            if picking.picking_type_id.code == 'outgoing':
                if ml.location_dest_id.usage == 'supplier':
                    # Return to Vendor
                    ml._update_consignment_return_qty()
                    processed = True
                else:
                    # Consignment Sale (to customer or internal consumption)
                    _logger.info("Calling _update_consignment_sale_qty for ml=%s", ml.id)
                    ml._update_consignment_sale_qty()
                    processed = True

            # 2. Consignment Incoming Moves (Customer Return or PO Receipt)
            if not processed and picking.picking_type_id.code == 'incoming':
                # Check for Customer Return (from customer location to internal)
                if ml.location_id.usage == 'customer':
                    ml._update_consignment_customer_return_qty()
                    processed = True
                else:
                    # PO Receipt
                    po = ml.move_id.purchase_line_id.order_id or picking.purchase_id
                    if po and po.is_consignment:
                        ml._create_or_update_consignment_stock_line()
                        processed = True
            
            if processed:
                ml.x_is_consignment_processed = True
                _logger.info("Marked ml=%s as processed", ml.id)
                    
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

        # Determine the warehouse for branch isolation
        warehouse_id = self.picking_id.picking_type_id.warehouse_id.id or self.location_id.warehouse_id.id

        domain = [
            ('product_id', '=', self.product_id.id),
            ('vendor_id', '=', vendor_id),
            ('lot_id', '=', self.lot_id.id),
            ('remaining_qty', '>', 0)
        ]
        
        # Match by product + vendor owner + lot
        # We search for the oldest consignment line that has remaining quantity
        cons_lines = self.env['pharmacy.consignment.stock.line'].search(domain, order='id asc')

        qty_to_attribute = self.quantity
        for line in cons_lines:
            if qty_to_attribute <= 0:
                break
            
            attribute_qty = min(qty_to_attribute, line.remaining_qty)
            line.sold_qty += attribute_qty
            qty_to_attribute -= attribute_qty
        
        # If there's still qty_to_attribute > 0, attribute to the first line found
        if qty_to_attribute > 0 and cons_lines:
            cons_lines[0].sold_qty += qty_to_attribute

    def _update_consignment_customer_return_qty(self):
        self.ensure_one()
        
        # Determine the vendor owner
        vendor_id = self.owner_id.id
        if not vendor_id and self.lot_id:
            tracking_line = self.env['pharmacy.consignment.stock.line'].search([
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id)
            ], limit=1)
            if tracking_line:
                vendor_id = tracking_line.vendor_id.id

        if not vendor_id:
            return

        # Determine the warehouse for branch isolation
        warehouse_id = self.picking_id.picking_type_id.warehouse_id.id or self.location_dest_id.warehouse_id.id

        domain = [
            ('product_id', '=', self.product_id.id),
            ('vendor_id', '=', vendor_id),
            ('lot_id', '=', self.lot_id.id),
            ('sold_qty', '>', 0)
        ]
        
        # Deduct from the newest tracking lines first (LIFO for returns)
        cons_lines = self.env['pharmacy.consignment.stock.line'].search(domain, order='id desc')

        qty_to_return = self.quantity
        for line in cons_lines:
            if qty_to_return <= 0:
                break
            
            return_qty = min(qty_to_return, line.sold_qty)
            line.sold_qty -= return_qty
            qty_to_return -= return_qty

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
