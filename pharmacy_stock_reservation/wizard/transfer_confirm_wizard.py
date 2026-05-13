from odoo import models, fields, api, _
from odoo.exceptions import UserError
class PharmacyTransferConfirmWizard(models.TransientModel):
    _name = 'pharmacy.transfer.confirm.wizard'
    _description = 'Transfer Availability Check — per product line'
    picking_id = fields.Many2one('stock.picking', required=True, readonly=True)
    line_ids = fields.One2many(
        'pharmacy.transfer.confirm.wizard.line',
        'wizard_id',
        string='Product Lines',
        readonly=True,
    )
    all_available = fields.Boolean(compute='_compute_all_available')
    warning_message = fields.Char(compute='_compute_all_available')
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        picking_id = self.env.context.get('default_picking_id')
        if not picking_id:
            return res
        picking = self.env['stock.picking'].browse(picking_id)
        StockQuant = self.env['stock.quant']
        lines = []
        for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            quants = StockQuant.search([
                ('product_id', '=', move.product_id.id),
                ('location_id', '=', move.location_id.id),
            ])
            on_hand = sum(quants.mapped('quantity'))
            reserved = sum(quants.mapped('pharmacy_reserved_qty'))
            available = on_hand - reserved
            requested = move.product_uom_qty
            if available >= requested - 1e-9:
                status = 'available'
            elif available > 0:
                status = 'reserved'
            else:
                status = 'not_enough'
            lines.append((0, 0, {
                'product_id': move.product_id.id,
                'location_id': move.location_id.id,
                'on_hand_qty': on_hand,
                'reserved_qty': reserved,
                'available_qty': available,
                'requested_qty': requested,
                'uom_id': move.product_uom.id,
                'status': status,
            }))
        res['line_ids'] = lines
        return res
    @api.depends('line_ids.status')
    def _compute_all_available(self):
        for wiz in self:
            not_enough = wiz.line_ids.filtered(lambda l: l.status == 'not_enough')
            wiz.all_available = not bool(not_enough)
            if not_enough:
                names = ', '.join(not_enough.mapped('product_id.display_name'))
                wiz.warning_message = _("Insufficient stock for: %s") % names
            else:
                wiz.warning_message = False
    def action_confirm(self):
        """Confirm the transfer — triggers reservation via stock.picking."""
        self.ensure_one()
        if not self.all_available:
            raise UserError(
                _("Cannot confirm: one or more products have insufficient available stock.\n%s")
                % (self.warning_message or '')
            )
        return self.picking_id.action_confirm()
    def action_force_confirm(self):
        """Confirm anyway (partial fill) — Inventory Manager only."""
        self.ensure_one()
        if not self.env.user.has_group(
            'pharmacy_base.group_inventory_manager'
        ):
            raise UserError(_("Only Inventory Managers can force-confirm a transfer with insufficient stock."))
        return self.picking_id.action_confirm()
class PharmacyTransferConfirmWizardLine(models.TransientModel):
    _name = 'pharmacy.transfer.confirm.wizard.line'
    _description = 'Transfer Confirmation Wizard Line'
    wizard_id = fields.Many2one('pharmacy.transfer.confirm.wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Source Location', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    on_hand_qty = fields.Float('On Hand', digits='Product Unit of Measure', readonly=True)
    reserved_qty = fields.Float('Reserved', digits='Product Unit of Measure', readonly=True)
    available_qty = fields.Float('Available', digits='Product Unit of Measure', readonly=True)
    requested_qty = fields.Float('Requested', digits='Product Unit of Measure', readonly=True)
    status = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Partially Reserved'),
        ('not_enough', 'Not Enough Stock'),
    ], string='Status', readonly=True)