from odoo import models, fields, api, _

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        res = super()._action_done()
        for ml in self:
            if ml.state == 'done':
                # Consignment Receipt
                if ml.picking_id.purchase_id.is_consignment and ml.picking_id.picking_type_id.code == 'incoming':
                    ml._create_or_update_consignment_stock_line()
                
                # Consignment Sale (Outgoing move with owner)
                elif ml.picking_id.picking_type_id.code == 'outgoing' and ml.owner_id:
                    ml._update_consignment_sale_qty()
                
                # Consignment Return to Vendor (Outgoing move to Vendor with owner)
                elif ml.picking_id.picking_type_id.code == 'outgoing' and ml.location_dest_id.usage == 'supplier' and ml.owner_id:
                    ml._update_consignment_return_qty()
                    
        return res

    def _create_or_update_consignment_stock_line(self):
        self.ensure_one()
        po_line = self.move_id.purchase_line_id
        if not po_line:
            # Fallback to searching PO line if not directly linked (though usually it is for receipts)
            po_line = self.env['purchase.order.line'].search([
                ('order_id', '=', self.picking_id.purchase_id.id),
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

    def _update_consignment_sale_qty(self):
        self.ensure_one()
        # Match by product + vendor owner + lot
        # We search for the oldest consignment line that has remaining quantity
        cons_lines = self.env['pharmacy.consignment.stock.line'].search([
            ('product_id', '=', self.product_id.id),
            ('vendor_id', '=', self.owner_id.id),
            ('lot_id', '=', self.lot_id.id),
            ('remaining_qty', '>', 0)
        ], order='id asc')

        qty_to_attribute = self.quantity
        for line in cons_lines:
            if qty_to_attribute <= 0:
                break
            
            # How much can we attribute to this line?
            # In a sale, we might be selling more than what was in a single PO
            # But here we match by lot, so it should be within the received qty of that lot in that PO.
            # However, if multiple POs have the same lot, we consume from the first one.
            attribute_qty = min(qty_to_attribute, line.remaining_qty)
            line.sold_qty += attribute_qty
            qty_to_attribute -= attribute_qty
        
        # If there's still qty_to_attribute > 0, it means we sold more than we tracked as received
        # for this specific lot/owner combination. This shouldn't happen in a strict system,
        # but for robustness we could log it or attribute to the first line anyway.
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
