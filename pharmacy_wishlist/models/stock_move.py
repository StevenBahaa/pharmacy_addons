# -*- coding: utf-8 -*-
from odoo import models, api
from collections import defaultdict

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        
        # Identify internal moves that might fulfill wishlists
        moves_to_check = self.filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'internal')
        if not moves_to_check:
            return res

        product_ids = moves_to_check.mapped('product_id.id')
        wishlist_records = self.env['pharmacy.wishlist'].sudo().search([
            ('product_id', 'in', product_ids),
            ('state', '=', 'not_called')
        ])
        
        if not wishlist_records:
            return res

        # Group wishlists by product to check stock once per product
        wishlists_by_product = defaultdict(lambda: self.env['pharmacy.wishlist'].sudo())
        for wl in wishlist_records:
            wishlists_by_product[wl.product_id.id] |= wl

        for product_id, wishlists in wishlists_by_product.items():
            # Get all internal locations for the companies of the wishlists
            companies = wishlists.mapped('company_id')
            locations = self.env['stock.location'].sudo().search([
                ('company_id', 'in', companies.ids),
                ('usage', '=', 'internal')
            ])
            
            # Efficiently check quantity across all relevant locations
            quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', product_id),
                ('location_id', 'in', locations.ids),
                ('quantity', '>', 0)
            ])
            
            if not quants:
                continue

            available_locations = quants.mapped('location_id')
            total_qty = sum(quants.mapped('quantity'))
            location_names = [loc.complete_name for loc in available_locations]

            for wl in wishlists:
                if total_qty >= wl.quantity:
                    wl.action_set_available(location_names)
                    
        return res
