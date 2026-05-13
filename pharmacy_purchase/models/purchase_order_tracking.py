# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import date_utils
from datetime import date


class PurchaseOrderLineTracking(models.Model):
    """
    Extended purchase.order.line model to add tracking fields
    for the Purchase Order Tracking screen (SC3-UC-03).
    """
    _inherit = 'purchase.order.line'

    # ─── Computed: Quantity Not Received (الفرق) ───────────────────────────────
    qty_not_received = fields.Float(
        string='Qty Not Received (الفرق)',
        compute='_compute_qty_not_received',
        store=True,
        digits='Product Unit of Measure',
        help='Quantity Ordered minus Quantity Received. '
             'Displayed in red if > 0, green if = 0.',
    )

    # ─── Computed: Delivery Status ──────────────────────────────────────────────
    delivery_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('partial', 'Partial'),
            ('received', 'Fully Received'),
            ('overdue', 'Overdue'),
        ],
        string='Delivery Status',
        compute='_compute_delivery_status',
        store=True,
        help='Computed delivery status for color-coding rows.',
    )

    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_delivery_status',
        store=True,
        help='True if Qty Not Received > 0 and Expected Arrival Date is in the past.',
    )

    # ─── Confirmation Date (from PO) ────────────────────────────────────────────
    confirmation_date = fields.Datetime(
        string='PO Confirmation Date',
        related='order_id.date_approve',
        store=True,
        readonly=True,
        help='Date the PO was confirmed (moved to Purchase Order state).',
    )

    # ─── Vendor (from PO) ───────────────────────────────────────────────────────
    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        related='order_id.partner_id',
        store=True,
        readonly=True,
    )

    # ─── Product display with internal ref ──────────────────────────────────────
    product_display_name = fields.Char(
        string='Product Display',
        compute='_compute_product_display_name',
        store=True,
        help='Product name with internal reference code in brackets.',
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Compute Methods
    # ──────────────────────────────────────────────────────────────────────────

    @api.depends('product_qty', 'qty_received')
    def _compute_qty_not_received(self):
        for line in self:
            line.qty_not_received = line.product_qty - line.qty_received

    @api.depends('qty_not_received', 'date_planned')
    def _compute_delivery_status(self):
        today = fields.Date.today()
        for line in self:
            not_received = line.qty_not_received
            date_planned = line.date_planned

            if not_received <= 0:
                line.delivery_status = 'received'
                line.is_overdue = False
            elif date_planned and date_planned.date() < today:
                line.delivery_status = 'overdue'
                line.is_overdue = True
            elif line.qty_received > 0:
                line.delivery_status = 'partial'
                line.is_overdue = False
            else:
                line.delivery_status = 'pending'
                line.is_overdue = False

    @api.depends('product_id', 'product_id.default_code', 'product_id.name')
    def _compute_product_display_name(self):
        for line in self:
            if line.product_id:
                ref = line.product_id.default_code
                name = line.product_id.name
                if ref:
                    line.product_display_name = f'[{ref}] {name}'
                else:
                    line.product_display_name = name
            else:
                line.product_display_name = ''


class PurchaseOrderTracking(models.Model):
    """
    Proxy model used as the base for the Purchase Order Tracking list view.
    This model extends purchase.order to expose PO-level summary fields
    for the grouped view header rows.
    """
    _inherit = 'purchase.order'

    # ─── PO-level aggregated totals ─────────────────────────────────────────────
    total_qty_ordered = fields.Float(
        string='Total Qty Ordered',
        compute='_compute_po_totals',
        digits='Product Unit of Measure',
    )

    total_qty_received = fields.Float(
        string='Total Qty Received',
        compute='_compute_po_totals',
        digits='Product Unit of Measure',
    )

    total_qty_not_received = fields.Float(
        string='Total Qty Not Received',
        compute='_compute_po_totals',
        digits='Product Unit of Measure',
    )

    po_tracking_status = fields.Selection(
        selection=[
            ('fully_received', 'Fully Received'),
            ('pending', 'Has Outstanding Quantities'),
            ('overdue', 'Has Overdue Lines'),
        ],
        string='PO Tracking Status',
        compute='_compute_po_totals',
    )

    has_pending_lines = fields.Boolean(
        string='Has Pending Lines',
        compute='_compute_po_totals',
    )

    @api.depends(
        'order_line.product_qty',
        'order_line.qty_received',
        'order_line.qty_not_received',
        'order_line.is_overdue',
    )
    def _compute_po_totals(self):
        for order in self:
            lines = order.order_line
            total_ordered = sum(lines.mapped('product_qty'))
            total_received = sum(lines.mapped('qty_received'))
            total_not_received = total_ordered - total_received

            order.total_qty_ordered = total_ordered
            order.total_qty_received = total_received
            order.total_qty_not_received = total_not_received
            order.has_pending_lines = total_not_received > 0

            if any(lines.mapped('is_overdue')):
                order.po_tracking_status = 'overdue'
            elif total_not_received > 0:
                order.po_tracking_status = 'pending'
            else:
                order.po_tracking_status = 'fully_received'
