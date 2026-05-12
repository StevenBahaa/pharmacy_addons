# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _check_security_constraints(self):
        for order in self.mapped('order_id'):
            # 1. Check Max Qty Override
            product_totals = defaultdict(float)
            for line in order.lines:
                if not line.product_id:
                    continue
                product = line.product_id.product_tmpl_id

                qty_in_base_uom = line.product_uom_id._compute_quantity(
                    line.qty,
                    line.product_id.uom_id,
                )
                product_totals[product.id] += qty_in_base_uom

                # 2. Check for Expired Lot Sale
                if line.pack_lot_ids:
                    for lot_selection in line.pack_lot_ids:
                        lot = self.env['stock.lot'].sudo().search([('name', '=', lot_selection.lot_name), ('product_id', '=', line.product_id.id)], limit=1)
                        if lot and lot.expiration_date and lot.expiration_date <= fields.Datetime.now():
                            # Log expired lot sale override
                            self.env['pharmacy.audit.log'].sudo().create({
                                'user_id': self.env.user.id,
                                'model_name': 'pos.order',
                                'res_id': order.id,
                                'action_type': 'expired_lot_sale',
                                'old_value': lot.expiration_date.strftime('%Y-%m-%d'),
                                'new_value': 'Sold',
                                'note': _('Expired Lot sold in POS: %s (Product: %s)') % (lot.name, line.product_id.display_name),
                            })

            for product_id, total_qty in product_totals.items():
                product = self.env['product.template'].browse(product_id)
                if product.max_qty_per_invoice and total_qty > product.max_qty_per_invoice:      
                    if self.env.user.has_group('pharmacy_base.group_pharmacy_manager') or \
                       self.env.user.has_group('pharmacy_base.group_pharmacist'):
                        # Log the override immutably
                        self.env['pharmacy.audit.log'].sudo().create({
                            'user_id': self.env.user.id,
                            'model_name': 'pos.order',
                            'res_id': order.id,
                            'action_type': 'qty_override',
                            'old_value': str(product.max_qty_per_invoice),
                            'new_value': str(total_qty),
                            'note': _('POS Max Qty Overridden for product: %s') % product.name,
                        })
                    else:
                        raise ValidationError(
                            _(
                                'You cannot sell more than %(max_qty)s packages of %(product)s '
                                'in a single POS order.\n'
                                'Current total: %(current_total)s\n'
                                'Only a Pharmacist or Pharmacy Manager can override this limit.'
                            ) % {
                                'max_qty': product.max_qty_per_invoice,
                                'product': product.name,
                                'current_total': total_qty,
                            }
                        )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_security_constraints()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self._check_security_constraints()
        return res
