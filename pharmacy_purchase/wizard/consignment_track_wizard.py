from odoo import models, fields, api

class ConsignmentTrackWizard(models.TransientModel):
    _name = "pharmacy.consignment.track.wizard"
    _description = "Consignment Track Stock Wizard"
    
    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    line_ids = fields.One2many(
        "pharmacy.consignment.track.wizard.line",
        "wizard_id",
        string="Lines",
    )

    def action_create_payment_bill(self):
        # TODO: Implement bill creation logic
        return {"type": "ir.actions.act_window_close"}


class ConsignmentTrackWizardLine(models.TransientModel):
    _name = "pharmacy.consignment.track.wizard.line"
    _description = "Consignment Track Stock Wizard Line"
    
    wizard_id = fields.Many2one(
        comodel_name='pharmacy.consignment.track.wizard',
        required=True,
        ondelete='cascade',
    )

    purchase_order_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
    )
    
    received_qty = fields.Float(readonly=True)
    sold_qty = fields.Float(readonly=True)
    already_paid_qty = fields.Float(readonly=True)
    payable_now_qty = fields.Float(readonly=True)
    payable_remaining_qty = fields.Float(readonly=True)

    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('partial', 'Partial'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='pending',
    )