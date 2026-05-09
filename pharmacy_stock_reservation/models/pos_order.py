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
    @api.model
    def _process_order(self, order, draft, **kwargs):
        # Prevent expired lots from being validated in POS
        self._check_pos_expiry_safety(order)
        return super()._process_order(order, draft, **kwargs)

    @api.model
    def _check_pos_expiry_safety(self, order_data):
        today = fields.Date.context_today(self)
        lines = order_data.get('data', {}).get('lines', [])
        for line_tuple in lines:
            if len(line_tuple) < 3:
                continue
            line_dict = line_tuple[2]
            pack_lot_ids = line_dict.get('pack_lot_ids', [])
            for lot_tuple in pack_lot_ids:
                if len(lot_tuple) < 3:
                    continue
                lot_dict = lot_tuple[2]
                lot_name = lot_dict.get('lot_name')
                if lot_name:
                    lot = self.env['stock.lot'].search([('name', '=', lot_name)], limit=1)
                    if lot and lot.expiration_date and lot.expiration_date.date() < today:
                        raise UserError(_(
                            "POS SAFETY ALERT: You scanned an expired lot (%s). "
                            "Sale has been blocked."
                        ) % lot.name)
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