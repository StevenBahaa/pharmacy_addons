# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        
        Wishlist = self.env['pharmacy.wishlist']
        for move in self:
            if move.state == 'done' and move.location_dest_id.usage == 'internal':
                product = move.product_id
                dest_location = move.location_dest_id
                
                # Search for pending wishlist items for this product
                wishlist_items = Wishlist.search([
                    ('product_id', '=', product.id),
                    ('state', '=', 'not_called')
                ])
                
                if wishlist_items:
                    # Check qty available in the destination location
                    # Note: We use quantity instead of qty_available for real-time stock check in specific location
                    quants = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', dest_location.id)
                    ])
                    total_qty = sum(quants.mapped('quantity'))
                    
                    for item in wishlist_items:
                        if total_qty >= item.quantity:
                            item.write({
                                'state': 'available',
                                'location_names': dest_location.complete_name
                            })
        return res
