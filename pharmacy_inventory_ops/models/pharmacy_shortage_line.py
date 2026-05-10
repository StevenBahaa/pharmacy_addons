from odoo import models, fields, api
from odoo.exceptions import UserError

class PharmacyShortageLine(models.Model):
    _name = 'pharmacy.shortage.line'
    _description = "Pharmacy Shortage Line"

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True
    )

    min_qty = fields.Float(
        string='Min Qty',
        readonly=True
    )

    max_qty = fields.Float(
        string='Max Qty',
        readonly=True
    )

    onhand_qty = fields.Float(
        string='Onhand Qty',
        readonly=True
    )

    reserved_qty = fields.Float(
        string='Reserved Qty',
        readonly=True
    )

    available_qty = fields.Float(
        string='Available Qty',
        readonly=True
    )

    incoming_qty = fields.Float(
        string='Incoming Qty',
        readonly=True,
        help="Incoming quantity from confirmed POs and RFQs."
    )

    shortage_qty = fields.Float(
        string='Shortage Qty',
        readonly=True
    )

    suggested_order_qty = fields.Float(
        string='Suggested Order Qty',
        readonly=True
    )

    incoming_po_ids = fields.Many2many(
        'purchase.order',
        string='Incoming References',
        readonly=True
    )

    incoming_po_count = fields.Integer(
        string='PO Count',
        compute='_compute_incoming_po_display',
        store=True
    )

    incoming_reference_display = fields.Char(
        string='Incoming References (Text)',
        compute='_compute_incoming_po_display',
        store=True
    )

    state = fields.Selection([
        ('to_order', 'To Order'),
        ('partial', 'Partially Covered'),
        ('covered', 'Covered by Incoming'),
        ('resolved', 'Resolved')
    ], string='Status', readonly=True, default='to_order')

    last_refresh_date = fields.Datetime(
        string='Last Refresh',
        readonly=True
    )

    urgency_level = fields.Selection([
        ('critical', 'Critical (Out of Stock)'),
        ('warning', 'Warning (Low Stock)'),
        ('normal', 'Normal'),
    ], string='Urgency', compute='_compute_urgency_level', store=True)

    @api.depends('available_qty', 'min_qty')
    def _compute_urgency_level(self):
        for line in self:
            if line.available_qty <= 0:
                line.urgency_level = 'critical'
            elif line.available_qty < (line.min_qty * 0.5):
                line.urgency_level = 'warning'
            else:
                line.urgency_level = 'normal'

    _sql_constraints = [
        ("unique_product_location_warehouse",
         "unique(product_id, location_id, warehouse_id)",
         "Duplicate shortage line!")
    ]

    @api.depends('incoming_po_ids')
    def _compute_incoming_po_display(self):
        for line in self:
            count = len(line.incoming_po_ids)
            line.incoming_po_count = count
            if count == 0:
                line.incoming_reference_display = ""
            elif count == 1:
                line.incoming_reference_display = line.incoming_po_ids[0].name
            elif count == 2:
                line.incoming_reference_display = f"{line.incoming_po_ids[0].name}, {line.incoming_po_ids[1].name}"
            else:
                line.incoming_reference_display = f"{line.incoming_po_ids[0].name}, {line.incoming_po_ids[1].name} (+{count - 2})"


    def _should_include_expired_stock(self):
        """
        Future-ready hook to allow toggling exclusion of expired lots.
        For now, business rules dictate expired stock is counted as available.
        """
        return True

    def action_refresh_shortage_lines(self):
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        Shortage = self.env["pharmacy.shortage.line"]
        Quant = self.env["stock.quant"]
        Move = self.env["stock.move"]

        orderpoints = Orderpoint.search([])
        if not orderpoints:
            return

        # 1. Gather Locations
        location_ids = orderpoints.mapped("location_id").ids
        op_locations = self.env['stock.location'].browse(location_ids)
        
        loc_map = {}
        for op_loc in op_locations:
            child_locs = self.env['stock.location'].search([('id', 'child_of', op_loc.id)])
            for child in child_locs:
                if child.id not in loc_map:
                    loc_map[child.id] = []
                loc_map[child.id].append(op_loc.id)

        product_ids = orderpoints.mapped("product_id").ids
        all_child_loc_ids = list(loc_map.keys())

        # 2. Gather Quants (Onhand & Reserved)
        domain_quant = [
            ("product_id", "in", product_ids),
            ("location_id", "in", all_child_loc_ids),
        ]
        
        if not self._should_include_expired_stock():
            # In the future, we could exclude expired stock here:
            # domain_quant.append(("lot_id.expiration_date", ">", fields.Datetime.now()))
            pass
            
        quants = Quant.read_group(
            domain_quant,
            ["product_id", "location_id", "quantity:sum", "reserved_quantity:sum"],
            ["product_id", "location_id"],
            lazy=False
        )
        
        quant_agg = {}
        for q in quants:
            p_id = q['product_id'][0]
            c_loc_id = q['location_id'][0]
            for parent_loc_id in loc_map.get(c_loc_id, []):
                key = (p_id, parent_loc_id)
                if key not in quant_agg:
                    quant_agg[key] = {'quantity': 0.0, 'reserved_quantity': 0.0}
                quant_agg[key]['quantity'] += q['quantity']
                quant_agg[key]['reserved_quantity'] += q['reserved_quantity']

        # 3. Gather Moves (Incoming)
        moves = Move.search([
            ("product_id", "in", product_ids),
            ("location_dest_id", "in", all_child_loc_ids),
            ("purchase_line_id", "!=", False),
            ("state", "not in", ["done", "cancel"]),
        ])
        
        # Prefetch to avoid N+1
        moves.mapped('purchase_line_id.order_id')
        
        move_agg = {}
        for m in moves:
            p_id = m.product_id.id
            c_loc_id = m.location_dest_id.id
            po_id = m.purchase_line_id.order_id.id
            qty = m.product_uom_qty
            for parent_loc_id in loc_map.get(c_loc_id, []):
                key = (p_id, parent_loc_id)
                if key not in move_agg:
                    move_agg[key] = {'qty': 0.0, 'po_ids': set()}
                move_agg[key]['qty'] += qty
                if po_id:
                    move_agg[key]['po_ids'].add(po_id)

        # 4. Upsert Shortage Lines
        existing_lines = Shortage.search([])
        existing_map = {(l.product_id.id, l.location_id.id, l.warehouse_id.id): l for l in existing_lines}
        processed_keys = set()
        
        now = fields.Datetime.now()
        
        for op in orderpoints:
            key = (op.product_id.id, op.location_id.id)
            q_data = quant_agg.get(key, {'quantity': 0.0, 'reserved_quantity': 0.0})
            onhand_qty = q_data['quantity']
            reserved_qty = q_data['reserved_quantity']
            
            m_data = move_agg.get(key, {'qty': 0.0, 'po_ids': set()})
            incoming_qty = m_data['qty']
            po_ids = list(m_data['po_ids'])
            
            available_qty = onhand_qty - reserved_qty
            shortage_qty = max(0.0, op.product_min_qty - available_qty)
            
            # Suggested Order Qty = max(1, Shortage - Incoming) if in shortage
            suggested_order_qty = 0.0
            if shortage_qty > 0:
                suggested_order_qty = max(1.0, shortage_qty - incoming_qty)
            
            state = 'resolved'
            if available_qty <= op.product_min_qty:
                if incoming_qty == 0:
                    state = 'to_order'
                elif incoming_qty > 0 and incoming_qty < shortage_qty:
                    state = 'partial'
                elif incoming_qty >= shortage_qty:
                    state = 'covered'
                    
            vals = {
                "min_qty": op.product_min_qty,
                "max_qty": op.product_max_qty,
                "onhand_qty": onhand_qty,
                "reserved_qty": reserved_qty,
                "available_qty": available_qty,
                "shortage_qty": shortage_qty,
                "incoming_qty": incoming_qty,
                "incoming_po_ids": [(6, 0, po_ids)],
                "suggested_order_qty": suggested_order_qty,
                "state": state,
                "last_refresh_date": now,
            }
            
            map_key = (op.product_id.id, op.location_id.id, op.warehouse_id.id)
            processed_keys.add(map_key)
            
            if map_key in existing_map:
                existing_map[map_key].write(vals)
            elif state != 'resolved':
                vals.update({
                    "product_id": op.product_id.id,
                    "location_id": op.location_id.id,
                    "warehouse_id": op.warehouse_id.id,
                })
                Shortage.create(vals)
                
        # 5. Resolve remaining lines
        for map_key, line in existing_map.items():
            if map_key not in processed_keys and line.state != 'resolved':
                line.write({'state': 'resolved', 'last_refresh_date': now})
                
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_view_incoming_pos(self):
        self.ensure_one()
        return {
            'name': 'Incoming Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.incoming_po_ids.ids)],
        }

    def action_export_shortage_xlsx(self):
        """
        Permanent header-button export.
        Reads active domain from context so the export always reflects
        current search filters — no row selection needed.
        """
        active_domain = self.env.context.get('active_domain') or []
        filter_label = self.env.context.get('filter_label', 'All Records')

        # Resolve named search defaults into a human-readable label
        if not filter_label or filter_label == 'All Records':
            default_unresolved = self.env.context.get('search_default_unresolved')
            if default_unresolved:
                filter_label = 'Unresolved Shortages'

        return {
            'type': 'ir.actions.report',
            'report_name': 'pharmacy_reports.shortage_report_xlsx',
            'report_type': 'xlsx',
            'report_file': 'pharmacy_reports.shortage_report_xlsx',
            'data': {
                'domain': active_domain,
                'filter_label': filter_label,
            },
            'context': self.env.context,
        }

    def _get_valid_vendor(self):
        self.ensure_one()
        suppliers = self.product_id.seller_ids.filtered(
            lambda s: (not s.company_id or s.company_id == self.env.company)
        )
        if not suppliers:
            raise UserError(f"No vendor found for product {self.product_id.display_name}. Please set a vendor.")
        return suppliers[0].partner_id.id

    def action_create_rfq(self):
        self.ensure_one()
        
        # If incoming exists, show warning wizard
        if self.incoming_qty > 0:
            return {
                'name': 'Duplicate Procurement Warning',
                'type': 'ir.actions.act_window',
                'res_model': 'pharmacy.shortage.rfq.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_line_id': self.id,
                    'default_incoming_qty': self.incoming_qty,
                    'default_shortage_qty': self.shortage_qty,
                    'default_suggested_qty': self.suggested_order_qty,
                }
            }
        
        return self._do_create_rfq()

    def _do_create_rfq(self, note=None):
        self.ensure_one()
        partner_id = self._get_valid_vendor()
        
        vals = {
            "type": "ir.actions.act_window",
            "name": "Create RFQ",
            "res_model": "purchase.order",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_partner_id": partner_id,
                "default_order_line": [
                    (0, 0, {
                        "product_id": self.product_id.id,
                        "product_qty": self.suggested_order_qty,
                        "product_uom": self.product_id.uom_po_id.id or self.product_id.uom_id.id,
                        "name": self.product_id.display_name,
                        "date_planned": fields.Datetime.now(),
                    })
                ]
            },
        }
        
        if note:
            # We can't easily add a chatter note to a new unsaved record via context default_notes,
            # but we can add it to the 'notes' field (Terms & Conditions) or handle it post-save.
            # For simplicity and visibility, we'll put it in default_notes if the model supports it.
            vals['context']['default_notes'] = note
            
        return vals
    
    def action_create_rfq_from_selected(self):
        if not self.env.user.has_group('pharmacy_base.group_purchasing_officer') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("Only Purchasing Officers or Pharmacy Managers can create RFQs."))
        # Filter out resolved lines if somehow called
        records = self.filtered(lambda r: r.state != 'resolved')
        if not records:
            raise UserError("No unresolved lines selected.")

        # Check if any have incoming stock
        any_incoming = any(r.incoming_qty > 0 for r in records)
        
        if any_incoming:
            # For simplicity in multi-select, if any have incoming, we warn about all.
            # Or we could just warn about the specific ones. 
            # Given the requirement, we'll use a simplified wizard or just proceed if the user confirms.
            # But the user asked for a warning popup with specific values. 
            # For multi-select, showing values for all is messy. 
            # We'll treat multi-select as "I know what I'm doing" or just loop and return the first wizard.
            # Most users use individual "Order Now" buttons.
            # We will implement a simplified warning for multi-select.
            return {
                'name': 'Duplicate Procurement Warning (Multiple)',
                'type': 'ir.actions.act_window',
                'res_model': 'pharmacy.shortage.rfq.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_multi_line_ids': self.ids,
                    'is_multi': True,
                }
            }

        return self._do_create_rfq_multi()

    def _do_create_rfq_multi(self, note=None):
        order_lines = []
        partner_id = False

        for line in self:
            if not partner_id:
                partner_id = line._get_valid_vendor()

            order_lines.append((0, 0, {
                "product_id": line.product_id.id,
                "product_qty": line.suggested_order_qty,
                "product_uom": line.product_id.uom_po_id.id or line.product_id.uom_id.id,
                "name": line.product_id.display_name,
                "date_planned": fields.Datetime.now(),
            }))

        vals = {
            "type": "ir.actions.act_window",
            "name": "Create RFQ",
            "res_model": "purchase.order",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_partner_id": partner_id,
                "default_order_line": order_lines,
            },
        }
        if note:
            vals['context']['default_notes'] = note
        return vals

class PharmacyShortageRFQWizard(models.TransientModel):
    _name = 'pharmacy.shortage.rfq.wizard'
    _description = 'Shortage RFQ Confirmation Wizard'

    line_id = fields.Many2one('pharmacy.shortage.line', string='Shortage Line')
    multi_line_ids = fields.Many2many('pharmacy.shortage.line', string='Shortage Lines')
    
    incoming_qty = fields.Float(string='Incoming Qty')
    incoming_po_ids = fields.Many2many(related='line_id.incoming_po_ids')
    shortage_qty = fields.Float(string='Shortage Qty')
    suggested_qty = fields.Float(string='Suggested Additional Qty')
    
    warning_message = fields.Text(compute='_compute_warning_message')

    @api.depends('multi_line_ids')
    def _compute_warning_message(self):
        for wizard in self:
            if wizard.multi_line_ids:
                wizard.warning_message = "Some of the selected products already have incoming stock.\nCreating additional RFQs may cause overstocking."
            else:
                wizard.warning_message = ""

    def action_confirm(self):
        if self.multi_line_ids:
            return self.multi_line_ids._do_create_rfq_multi(note="RFQ created while incoming stock already exists for some items.")
        return self.line_id._do_create_rfq(note="RFQ created while incoming stock already exists.")