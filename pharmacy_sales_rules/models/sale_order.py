from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    enable_product_commission = fields.Boolean(
        string='Enable Product Commission',
        related='company_id.enable_product_commission',
        store=False,
        readonly=True
    )

    def action_confirm(self):
        # ✅ allow wizard bypass
        if self.env.context.get('skip_low_stock_check'):
            res = super().action_confirm()
            # =========================
            # 🔥 LOG AFTER CONFIRMATION
            # =========================
            for order in self:
                product_totals = defaultdict(float)
                valid_lines = order.order_line.filtered(
                    lambda l: l.product_id and not l.display_type
                )
                for line in valid_lines:
                    product = line.product_id
                    tmpl = product.product_tmpl_id
                    qty_in_base = line.product_uom._compute_quantity(
                        line.product_uom_qty,
                        product.uom_id,
                    )
                    product_totals[tmpl.id] += qty_in_base
                for tmpl_id, total_qty in product_totals.items():
                    tmpl = self.env['product.template'].browse(tmpl_id)
                    if not tmpl.low_stock_limit or not tmpl.max_qty_low_stock:
                        continue
                    product = tmpl.product_variant_id
                    stock = product.with_context(
                        warehouse=order.warehouse_id.id
                    ).qty_available
                    if stock <= tmpl.low_stock_limit and total_qty > tmpl.max_qty_low_stock:
                        self.env['low.stock.log'].create({
                            'user_id': self.env.user.id,
                            'product_id': product.id,
                            'quantity': total_qty,
                            'stock_at_time': stock,
                            'order_ref': order.name,
                            'source': 'sale',
                        })
            return res
        # =========================
        # 🚨 PRE-CONFIRM CHECK
        # =========================
        Wizard = self.env['low.stock.warning.wizard']
        for order in self:
            product_totals = defaultdict(float)
            warning_lines = []
            valid_lines = order.order_line.filtered(
                lambda l: l.product_id and not l.display_type
            )
            for line in valid_lines:
                product = line.product_id
                tmpl = product.product_tmpl_id
                qty_in_base = line.product_uom._compute_quantity(
                    line.product_uom_qty,
                    product.uom_id,
                )
                product_totals[tmpl.id] += qty_in_base
            for tmpl_id, total_qty in product_totals.items():
                tmpl = self.env['product.template'].browse(tmpl_id)
                if not tmpl.low_stock_limit or not tmpl.max_qty_low_stock:
                    continue
                product = tmpl.product_variant_id
                stock = product.with_context(
                    warehouse=order.warehouse_id.id
                ).qty_available
                if stock <= tmpl.low_stock_limit and total_qty > tmpl.max_qty_low_stock:
                    warning_lines.append((0, 0, {
                        'product_id': product.id,
                        'stock': stock,
                        'requested_qty': total_qty,
                        'max_qty': tmpl.max_qty_low_stock,
                    }))
            # 🚨 OPEN WIZARD
            if warning_lines:
                wizard = Wizard.create({
                    'order_id': order.id,
                    'line_ids': warning_lines,
                })
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Low Stock Warning'),
                    'res_model': 'low.stock.warning.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
                }
        return super().action_confirm()


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_manufacturer = fields.Boolean(string='Is Manufacturer')