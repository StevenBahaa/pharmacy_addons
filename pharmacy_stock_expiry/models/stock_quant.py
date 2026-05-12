import logging
from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError
from collections import defaultdict
_logger = logging.getLogger(__name__)
import math

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    x_expiry_month_year = fields.Char(
        related='lot_id.x_expiry_month_year',
        string='Expiry Date (MM/YYYY)',
        store=True,
    )

    x_transfer = fields.Boolean(string="Transfer (تحويل)")
    is_expired = fields.Boolean(
        string="Is Expired",
        compute="_compute_is_expired",
        store=True,
    )

    boxes_qty = fields.Float(compute="_compute_qty_display", store=True)
    units_qty = fields.Float(compute="_compute_qty_display", store=True)

    lot_expiry_date = fields.Date(
        related='lot_id.expiry_date',
        store=True,
        string="Expiry Date",
    )

    barcode = fields.Char(compute="_compute_barcode", store=True)
    expiring_days = fields.Integer(compute="_compute_expiring_days", store=True)

    transfer_status = fields.Char(
        string="Status",
        compute="_compute_transfer_status",
    )

    @api.depends('is_expired', 'expiring_days')
    def _compute_transfer_status(self):
        for rec in self:
            if rec.is_expired:
                rec.transfer_status = '✅ Expired — can transfer'
            elif rec.expiring_days <= 90:
                rec.transfer_status = '⚠️ Near-expiry — cannot transfer yet'
            else:
                rec.transfer_status = 'cannot transfer yet'

    def move_expired_products(self):
        expired_quants = self.search([
            ('lot_id.life_date', '<', fields.Datetime.now()),
            ('location_id.is_expired_location', '=', False),
            ('quantity', '>', 0)
        ])

        expired_location = self.env['stock.location'].search([
            ('is_expired_location', '=', True)
        ], limit=1)

        for quant in expired_quants:
            self.env['stock.move'].create({
                'name': 'Move Expired Product',
                'product_id': quant.product_id.id,
                'product_uom_qty': quant.quantity,
                'location_id': quant.location_id.id,
                'location_dest_id': expired_location.id,
            })

    @api.model
    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = super()._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)
        
        # Harden FEFO: Do not gather expired lots for reservation
        if location_id.usage == 'internal':
            domain.append('|')
            domain.append(('lot_id.expiration_date', '>=', fields.Datetime.now()))
            domain.append(('lot_id.expiration_date', '=', False))
            
        return domain
    
    def _get_inventory_domain(self):
        domain = super()._get_inventory_domain()

        domain = ['|',
            ('location_id.usage', '=', 'internal'),
            ('location_id.usage', '=', 'expired')
        ]

        return domain

    # ------------------------------------------------------------------ #
    #  Computed fields                                                     #
    # ------------------------------------------------------------------ #

    @api.depends('lot_id.expiry_date')
    def _compute_expiring_days(self):
        today = date.today()
        for rec in self:
            if rec.lot_id and rec.lot_id.expiry_date:
                rec.expiring_days = (rec.lot_id.expiry_date - today).days
            else:
                rec.expiring_days = 9999

    @api.depends('product_id.barcode_line_ids.name')
    def _compute_barcode(self):
        for rec in self:
            rec.barcode = rec.product_id.barcode_line_ids[:1].name or False

    @api.depends('lot_id.expiry_date', 'location_id')
    def _compute_is_expired(self):
        today = date.today()
        for rec in self:
            rec.is_expired = bool(
                rec.lot_id
                and rec.lot_id.expiry_date
                and today > rec.lot_id.expiry_date
            )

    @api.depends('quantity', 'product_id.units_per_package', 'product_id.sell_as')
    def _compute_qty_display(self):
        for rec in self:
            u = rec.product_id.units_per_package or 1
            if rec.product_id.sell_as == 'unit':
                rec.boxes_qty = int(rec.quantity)
                rec.units_qty =  math.ceil(rec.quantity * u - (rec.boxes_qty * u))
            else:
                rec.units_qty = rec.quantity
                rec.boxes_qty = rec.quantity

    
    def _get_expired_location_for_warehouse(self, source_location):
        warehouse = self.env['stock.warehouse'].search(
            [('view_location_id', 'parent_of', source_location.id)], limit=1
        )
        if warehouse:
            # Flagged expired location inside this warehouse
            loc = self.env['stock.location'].search([
                ('is_expired_location', '=', True),
                ('id', 'child_of', warehouse.view_location_id.id),
            ], limit=1)
            if loc:
                return loc
            # Any expired-type location inside this warehouse
            loc = self.env['stock.location'].search([
                ('usage', '=', 'expired'),
                ('id', 'child_of', warehouse.view_location_id.id),
            ], limit=1)
            if loc:
                return loc
        # Global fallback: any flagged expired location
        loc = self.env['stock.location'].search(
            [('is_expired_location', '=', True)], limit=1
        )
        if loc:
            return loc
        return self.env['stock.location'].search(
            [('usage', '=', 'expired')], limit=1
        )
    
    def action_transfer_to_expired(self):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("Only Inventory or Pharmacy Managers can transfer expired medicines."))
        if not self:
            raise UserError(_("No records selected."))

        quants = self.filtered(lambda q: q.quantity > 0 and q.lot_id and q.is_expired)
        if not quants:
            raise UserError(_("No valid expired quantities to transfer."))

        groups = defaultdict(lambda: self.env['stock.quant'])
        for q in quants:
            groups[q.location_id.id] |= q

        total_lots = 0

        for _loc_id, loc_quants in groups.items():
            source_location = loc_quants[0].location_id
            expired_location = self._get_expired_location_for_warehouse(source_location)

            if not expired_location:
                raise UserError(_(
                    "No expired location found for the warehouse of '%s'.\n"
                    "Please create a location under WH and enable the "
                    "'Expired Location' toggle on it."
                ) % source_location.complete_name)

            _logger.info(
                "EXPIRED TRANSFER: %s → %s (type=%s)",
                source_location.complete_name,
                expired_location.complete_name,
                expired_location.usage,
            )

            # ----------------------------------------------------------
            # Use _update_available_quantity — the correct low-level API
            # for moving stock to/from non-internal locations (expired,
            # scrap, virtual, etc.).  It directly writes stock.quant rows
            # without going through picking/move validation rules.
            # ----------------------------------------------------------
            Quant = self.env['stock.quant'].sudo()

            for quant in loc_quants:
                qty = quant.quantity
                product = quant.product_id
                lot = quant.lot_id
                src = quant.location_id

                _logger.info(
                    "EXPIRED TRANSFER: moving %s x %s (lot=%s) from %s to %s",
                    qty, product.display_name, lot.name,
                    src.complete_name, expired_location.complete_name,
                )

                # Deduct from source
                Quant._update_available_quantity(
                    product, src, -qty,
                    lot_id=lot,
                )

                # Add to expired destination
                Quant._update_available_quantity(
                    product, expired_location, qty,
                    lot_id=lot,
                )

            # ----------------------------------------------------------
            # Create a stock.picking record for traceability only
            # (state = done immediately via direct write, no validation)
            # ----------------------------------------------------------
            warehouse = self.env['stock.warehouse'].search(
                [('view_location_id', 'parent_of', source_location.id)], limit=1
            )
            picking_type = False
            if warehouse:
                picking_type = self.env['stock.picking.type'].search([
                    ('code', '=', 'internal'),
                    ('warehouse_id', '=', warehouse.id),
                ], limit=1)
            if not picking_type:
                picking_type = self.env['stock.picking.type'].search(
                    [('code', '=', 'internal')], limit=1
                )

            if picking_type:
                picking = self.env['stock.picking'].sudo().create({
                    'picking_type_id': picking_type.id,
                    'location_id': source_location.id,
                    'location_dest_id': expired_location.id,
                    'origin': 'Expired Transfer',
                    'x_transfer_tag': 'Expired Transfer',
                    'state': 'done',  # mark done directly — traceability only
                })

                for quant in loc_quants:
                    move = self.env['stock.move'].sudo().create({
                        'name': quant.product_id.display_name,
                        'picking_id': picking.id,
                        'product_id': quant.product_id.id,
                        'product_uom_qty': quant.quantity,
                        'product_uom': quant.product_id.uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': expired_location.id,
                    })
                    self.env['stock.move.line'].sudo().create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': quant.product_id.id,
                        'product_uom_id': quant.product_id.uom_id.id,
                        'quantity': quant.quantity,
                        'location_id': source_location.id,
                        'location_dest_id': expired_location.id,
                        'lot_id': quant.lot_id.id,
                    })

                _logger.info("EXPIRED TRANSFER: traceability picking id=%s created (state=done)", picking.id)

            total_lots += len(loc_quants)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    '%s medicine lot(s) successfully transferred to Expired stock.'
                ) % total_lots,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }
    # ------------------------------------------------------------------ #
    #  Open wizards from list view buttons                                #
    # ------------------------------------------------------------------ #

    def action_open_transfer_wizard(self):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("You are not authorized to perform this action."))
        # self = whatever rows the user selected in the list
        expired = self.filtered(lambda q: q.is_expired and q.quantity > 0 and q.lot_id)
        if not expired:
            raise UserError(_("Please select at least one expired lot to transfer."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'expired.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_quant_ids': [(6, 0, expired.ids)]},
        }

    def action_open_export_wizard(self):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("You are not authorized to perform this action."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'expired.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }
    def action_open_expired_report_wizard(self):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("You are not authorized to perform this action."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'expired.medicines.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }

    def action_refresh(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}