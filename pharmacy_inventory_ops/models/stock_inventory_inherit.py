# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
# class StockQuant(models.Model):
#     """
#     Extend stock.quant to add mandatory reason for daily spot-check adjustments
#     made directly on the standard Physical Inventory screen.
#     """
#     _inherit = 'stock.quant'
#     pharmacy_adjustment_reason = fields.Text(
#         string='Adjustment Reason',
#         help='Mandatory reason when adjusting on-hand quantity (pharmacy compliance).',
#     )
#     def action_apply_inventory(self):
#         """
#         Override to enforce reason when the quantity has changed.
#         Skipped when called from pharmacy.count._apply_inventory_adjustments
#         (which already validated reasons).
#         """
#         if not self.env.context.get('skip_pharmacy_reason_check'):
#             for quant in self:
#                 if (
#                     quant.inventory_quantity != quant.quantity
#                     and not quant.pharmacy_adjustment_reason
#                     and not self.env.context.get('inventory_reason')
#                 ):
#                     raise UserError(
#                         _(
#                             'Please provide an adjustment reason for "%s" before validating.',
#                             quant.product_id.display_name,
#                         )
#                     )
#         return super().action_apply_inventory()
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
class StockQuant(models.Model):
    _inherit = 'stock.quant'
    # pharmacy_adjustment_reason = fields.Text(
    #     string='Adjustment Reason',
    #     help='Mandatory reason when adjusting on-hand quantity (pharmacy compliance).',
    # )
    inventory_reason = fields.Text(
        string='Adjustment Reason',
        help='Mandatory reason when adjusting on-hand quantity (pharmacy compliance).',
        copy=False,
    )
    def action_apply_inventory(self):
        """
        Require adjustment reason when changing inventory manually.
        Skipped for pharmacy.count automated adjustments because
        those already validate discrepancy reasons.
        """
        if not self.env.context.get('skip_pharmacy_reason_check'):
            for quant in self:
                has_difference = (
                    float_compare(
                        quant.inventory_quantity,
                        quant.quantity,
                        precision_rounding=quant.product_uom_id.rounding,
                    ) != 0
                )
                if (
                    has_difference
                    and not quant.inventory_reason
                    and not self.env.context.get('inventory_reason')
                ):
                    raise UserError(
                        _(
                            'Please provide an adjustment reason for "%s" before validating.'
                        ) % quant.product_id.display_name
                    )
        return super().action_apply_inventory()