from odoo import models, fields , api 
from odoo.exceptions import UserError



import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_consignment_bill = fields.Boolean(
        string='Consignment Bill', 
        default=False,
        copy=False
    )

    def action_post(self):
        res = super(AccountMove, self).action_post()
        _logger.info("PHARMACY_PURCHASE: action_post called for move(s) %s", self.ids)
        for move in self:
            if move.move_type == 'in_invoice':
                _logger.info("PHARMACY_PURCHASE: Processing Vendor Bill %s", move.name)
                products_map = {}
                # collect max discount per product template
                for line in move.invoice_line_ids:
                    _logger.info("PHARMACY_PURCHASE: Line %s - Product: %s - Discount: %s", line.id, line.product_id.name, line.discount)
                    product = line.product_id.product_tmpl_id
                    if not product:
                        continue
                    if product not in products_map:
                        products_map[product] = []
                    products_map[product].append(line.discount or 0.0)

                # update products and create history
                for product, discounts in products_map.items():
                    max_discount = max(discounts)
                    old_discount = product.x_last_purchase_discount
                    _logger.info("PHARMACY_PURCHASE: Updating Product %s - Old Discount: %s - New Discount: %s", product.name, old_discount, max_discount)
                    product.sudo().x_last_purchase_discount = max_discount

                    # create history with sudo as this is an automated system log
                    history = self.env['product.discount.history'].sudo().create({
                        'product_tmpl_id': product.id,
                        'supplier_id': move.partner_id.id,
                        'invoice_id': move.id,
                        'discount': max_discount,
                        'date': move.invoice_date,
                    })
                    _logger.info("PHARMACY_PURCHASE: Created History Record %s", history.id)

                    # chatter log
                    product.message_post(body=f"""
                        <b>Last Purchase Discount Updated</b><br/>
                        Old: {old_discount}%<br/>
                        New: {max_discount}%<br/>
                        Supplier: {move.partner_id.name}<br/>
                        Invoice: {move.name}
                    """)
            
            # Update billed_qty on consignment stock lines
            if move.is_consignment_bill and move.state == 'posted':
                payments = self.env['pharmacy.consignment.payment'].search([('vendor_bill_id', '=', move.id)])
                for payment in payments:
                    if payment.consignment_stock_line_id:
                        payment.consignment_stock_line_id.billed_qty += payment.billed_qty
        return res

    def button_draft(self):
        for move in self:
            if move.move_type == 'in_invoice':
                for line in move.invoice_line_ids:
                    product = line.product_id.product_tmpl_id
                    if not product:
                        continue

                    # find last posted invoice for this product
                    last_invoice = self.env['account.move'].search([
                        ('move_type', '=', 'in_invoice'),
                        ('state', '=', 'posted'),
                        ('id', '!=', move.id),
                        ('invoice_line_ids.product_id.product_tmpl_id', '=', product.id)
                    ], order='invoice_date desc, id desc', limit=1)

                    if last_invoice:
                        prev_discounts = last_invoice.invoice_line_ids.filtered(
                            lambda l: l.product_id.product_tmpl_id == product
                        ).mapped('discount')
                        product.x_last_purchase_discount = max(prev_discounts) if prev_discounts else 0.0
                    else:
                        product.x_last_purchase_discount = 0.0

            if move.is_consignment_bill and move.state == 'posted':
                payments = self.env['pharmacy.consignment.payment'].search([('vendor_bill_id', '=', move.id)])
                for payment in payments:
                    if payment.consignment_stock_line_id:
                        payment.consignment_stock_line_id.billed_qty -= payment.billed_qty
        return super().button_draft()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_consignment_payment_line = fields.Boolean(
        string='Consignment Payment Line',
        default=False,
        copy=False
    )

    def write(self, vals):
        protected_fields = ['quantity', 'price_unit', 'discount', 'product_id', 'account_id', 'partner_id']
        
        for line in self:
            if line.is_consignment_payment_line and line.move_id.is_consignment_bill and line.move_id.state != 'cancel':
                for f in protected_fields:
                    if f in vals:
                        old_val = line[f]
                        if hasattr(old_val, 'id'):
                            old_val = old_val.id
                        new_val = vals[f]
                        
                        if not old_val and not new_val:
                            continue
                            
                        if isinstance(old_val, float) or isinstance(new_val, float):
                            if abs(float(old_val or 0.0) - float(new_val or 0.0)) < 0.0001:
                                continue
                                
                        if old_val != new_val:
                            raise UserError(
                                f"You cannot change critical fields ({f}) of a consignment bill line."
                            )
                            
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_consignment_payment(self):
        for line in self:
            if line.is_consignment_payment_line and line.move_id.is_consignment_bill and line.move_id.state != 'cancel':
                raise UserError("You cannot delete a consignment payment line from a consignment bill.")