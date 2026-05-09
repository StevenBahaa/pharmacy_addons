from odoo import models, fields, api, _
from odoo.exceptions import UserError
class PosOrder(models.Model):
    _inherit = 'pos.order'
    def _check_pharmacy_stock_availability(self):
        """
        Validate that each order line does not exceed available (unreserved) qty
        before the POS order is confirmed / invoiced.
        """
        StockQuant = self.env['stock.quant']
        for order in self:
            location = order.config_id.picking_type_id.default_location_src_id
            if not location:
                continue
            for line in order.lines:
                product = line.product_id
                if product.type != 'product':
                    continue
                available = StockQuant._get_available_quantity(product, location)
                if line.qty > available + 1e-9:
                    reserved = StockQuant._get_pharmacy_reserved(product, location)
                    raise UserError(_(
                        "Cannot complete POS sale.\n\n"
                        "Product: %(product)s\n"
                        "Requested: %(req).2f\n"
                        "Available: %(avail).2f\n"
                        "Reserved for transfers: %(res).2f\n\n"
                        "Please reduce quantity or contact the inventory manager.",
                        product=product.display_name,
                        req=line.qty,
                        avail=available,
                        res=reserved,
                    ))
    def action_pos_order_paid(self):
        self._check_pharmacy_stock_availability()
        return super().action_pos_order_paid()
    def _process_order(self, order, draft, existing_order):
        # Also check on process for robustness
        return super()._process_order(order, draft, existing_order)
class PosSession(models.Model):
    _inherit = 'pos.session'
    def _loader_params_product_product(self):
        """Add pharmacy availability fields to POS loader."""
        result = super()._loader_params_product_product()
        result['search_params']['fields'].extend([
            'pharmacy_reserved_qty',
            'pharmacy_available_qty',
        ])
        return result