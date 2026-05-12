from odoo.exceptions import UserError
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
        if not self.env.user.has_group('pharmacy_base.group_purchasing_officer') and \
           not self.env.user.has_group('pharmacy_base.group_accounting_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError("You are not authorized to create consignment vendor bills.")
        self.ensure_one()

        payable_lines = self.line_ids.filtered(lambda l: l.payable_now_qty > 0)
        if not payable_lines:
            raise UserError("No new sold units to pay for.")

        po = self.purchase_order_id

        invoice_lines = []
        for line in payable_lines:
            po_line = line.purchase_order_line_id

            invoice_lines.append((0, 0, {
                "product_id": line.product_id.id,
                "name": f"{po_line.name or line.product_id.display_name} (Lot: {line.lot_id.name})",
                "quantity": line.payable_now_qty,
                "price_unit": po_line.price_unit,
                "purchase_line_id": po_line.id,
                "is_consignment_payment_line": True,
                "account_id": line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id,
            }))

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": po.partner_id.id,
            "invoice_origin": po.name,
            "invoice_date": fields.Date.context_today(self),
            "invoice_line_ids": invoice_lines,
            "is_consignment_bill": True,
        })

        # Link payments to tracking lines
        for line, inv_line in zip(payable_lines, bill.invoice_line_ids):
            self.env["pharmacy.consignment.payment"].create({
                "purchase_order_id": po.id,
                "purchase_order_line_id": line.purchase_order_line_id.id,
                "consignment_stock_line_id": line.consignment_stock_line_id.id,
                "product_id": line.product_id.id,
                "lot_id": line.lot_id.id,
                "vendor_bill_id": bill.id,
                "vendor_bill_line_id": inv_line.id,
                "billed_qty": line.payable_now_qty,
            })

        po.message_post(
            body=f"Consignment vendor bill {bill.name or bill.ref or bill.id} created for sold unpaid quantities."
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Vendor Bill",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": bill.id,
            "target": "current",
        }

    def action_create_backorder(self):
        if not self.env.user.has_group('pharmacy_base.group_purchasing_officer') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError("You are not authorized to request backorders.")
        self.ensure_one()

        pickings = self.purchase_order_id.picking_ids.filtered(
            lambda picking: picking.state not in ('done', 'cancel')
        )
        if not pickings:
            raise UserError("No pending pickings to backorder.")

        self.purchase_order_id.message_post(
            body="Backorder requested from Consignment Tracking Wizard."
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Inventory Transfers",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", pickings.ids)],
            "target": "current",
        }

class ConsignmentTrackWizardLine(models.TransientModel):
    _name = "pharmacy.consignment.track.wizard.line"
    _description = "Consignment Track Stock Wizard Line"
    
    wizard_id = fields.Many2one(
        comodel_name='pharmacy.consignment.track.wizard',
        required=True,
        ondelete='cascade',
    )

    consignment_stock_line_id = fields.Many2one(
        comodel_name='pharmacy.consignment.stock.line',
        readonly=True,
    )

    purchase_order_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
    )

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        readonly=True,
    )

    expiry_date = fields.Date(readonly=True)
    expiry_display = fields.Char(string='Expiry', compute='_compute_expiry_display')

    @api.depends('expiry_date')
    def _compute_expiry_display(self):
        for line in self:
            if line.expiry_date:
                line.expiry_display = line.expiry_date.strftime('%m/%Y')
            else:
                line.expiry_display = ''
    
    received_qty = fields.Float(readonly=True)
    sold_qty = fields.Float(readonly=True)
    already_billed_qty = fields.Float(readonly=True)
    payable_now_qty = fields.Float(readonly=True)
    remaining_qty = fields.Float(readonly=True)

    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('partial', 'Partial'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='pending',
    )
