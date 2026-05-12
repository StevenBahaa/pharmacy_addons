from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PharmacyCount(models.Model):
    """
    Pharmacy Inventory Count — header record.
    Covers both Daily Spot-Check and Periodic Full Count sessions.
    """
    _name = 'pharmacy.count'
    _description = 'Pharmacy Inventory Count'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'count_date desc, id desc'

    # ------------------------------------------------------------------ #
    # Basic fields
    # ------------------------------------------------------------------ #
    # barcode = fields.Char(compute="_compute_barcode", store=True)
    # @api.depends('product_id.barcode_line_ids.name')
    # def _compute_barcode(self):
    #     for rec in self:
    #         rec.barcode = rec.product_id.barcode_line_ids[:1].name or False
    barcode_scan_input = fields.Char(string='Scan Barcode', copy=False, store=False)
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    count_type = fields.Selection(
        selection=[
            ('daily', 'Daily Spot-Check'),
            ('periodic', 'Periodic Full Count'),
        ],
        string='Count Type',
        required=True,
        default='daily',
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Validated'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    count_date = fields.Date(
        string='Count Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        tracking=True,
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
        tracking=True,
    )
    category_id = fields.Many2one(
        comodel_name='product.category',
        string='Product Category',
        tracking=True,
    )
    responsible_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Text(string='Internal Notes')

    line_ids = fields.One2many(
        comodel_name='pharmacy.count.line',
        inverse_name='count_id',
        string='Count Lines',
    )

    # ------------------------------------------------------------------ #
    # Summary computed fields
    # ------------------------------------------------------------------ #
    total_lines = fields.Integer(
        string='Total Products',
        compute='_compute_summary',
        store=True,
    )
    counted_lines = fields.Integer(
        string='Counted',
        compute='_compute_summary',
        store=True,
    )
    not_counted_lines = fields.Integer(
        string='Not Yet Counted',
        compute='_compute_summary',
        store=True,
    )
    discrepancy_lines = fields.Integer(
        string='With Discrepancy',
        compute='_compute_summary',
        store=True,
    )
    count_progress = fields.Float(
        string='Progress (%)',
        compute='_compute_summary',
        store=True,
    )

    # ------------------------------------------------------------------ #
    # Computed / depends
    # ------------------------------------------------------------------ #
    @api.depends('line_ids.counted_status', 'line_ids.difference')
    def _compute_summary(self):
        for rec in self:
            lines = rec.line_ids
            total = len(lines)
            counted = lines.filtered(lambda l: l.counted_status == 'counted')
            discrepancy = lines.filtered(
                lambda l: l.counted_status == 'counted' and l.difference != 0
            )
            rec.total_lines = total
            rec.counted_lines = len(counted)
            rec.not_counted_lines = total - len(counted)
            rec.discrepancy_lines = len(discrepancy)
            rec.count_progress = (len(counted) / total * 100) if total else 0.0

    # ------------------------------------------------------------------ #
    # Sequence
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_code = (
                    'pharmacy.count.daily'
                    if vals.get('count_type') == 'daily'
                    else 'pharmacy.count.periodic'
                )
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    def action_start(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Count is not in Draft state.'))
            rec.state = 'in_progress'

    def action_validate(self):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("Only Inventory or Pharmacy Managers can validate counts."))
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise UserError(_('Only Draft or In-Progress counts can be validated.'))

            # --- Periodic: all lines must be counted or marked not-found ---
            if rec.count_type == 'periodic':
                pending = rec.line_ids.filtered(
                    lambda l: l.counted_status == 'not_started'
                )
                if pending:
                    raise UserError(
                        _(
                            'Cannot validate: %d product(s) have not been counted yet. '
                            'Please count them or mark them as "Not Found".',
                            len(pending),
                        )
                    )

            # --- All lines must have a reason if there is a discrepancy ---
            missing_reason = rec.line_ids.filtered(
                lambda l: l.difference != 0 and not l.reason
            )
            if missing_reason:
                raise UserError(
                    _(
                        'Reason is mandatory for all lines with a discrepancy. '
                        'Missing on: %s',
                        ', '.join(missing_reason.mapped('product_id.display_name')),
                    )
                )

            # --- For daily spot-check: at least one global reason is needed ---
            if rec.count_type == 'daily':
                lines_with_delta = rec.line_ids.filtered(lambda l: l.difference != 0)
                if lines_with_delta:
                    missing = lines_with_delta.filtered(lambda l: not l.reason)
                    if missing:
                        raise UserError(
                            _(
                                'Please provide a reason for each product with a '
                                'discrepancy before validating.'
                            )
                        )

            # --- Create stock moves / inventory adjustments ---
            rec._apply_inventory_adjustments()
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('A validated count cannot be cancelled.'))
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('A validated count cannot be reset.'))
            rec.state = 'draft'

    # ------------------------------------------------------------------ #
    # Inventory adjustment logic
    # ------------------------------------------------------------------ #
    def _apply_inventory_adjustments(self):
        """
        For each line where counted_qty ≠ expected_qty, create a stock
        inventory adjustment (quant update) with the reason in the note.
        """
        self.ensure_one()
        StockQuant = self.env['stock.quant']

        for line in self.line_ids.filtered(lambda l: l.counted_qty is not False):
            location = line.location_id or (
                self.warehouse_id.lot_stock_id if self.warehouse_id
                else self.env.ref('stock.stock_location_stock')
            )
            quants = StockQuant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', location.id),
            ])
            if quants:
                quant = quants[0]
            else:
                quant = StockQuant.create({
                    'product_id': line.product_id.id,
                    'location_id': location.id,
                    'quantity': 0.0,
                })

            # Use the official _apply_inventory method (Odoo 18)
            # quant.with_context(inventory_mode=True).write({
            #     'inventory_quantity': line.counted_qty,
            #     'inventory_reason': line.reason or '',
            # })
            # quant.action_apply_inventory()
            quant.with_context(
                inventory_mode=True,
                skip_pharmacy_reason_check=True,
            ).write({
                'inventory_quantity': line.counted_qty,
                'inventory_reason': line.reason or '',
            })

            quant.action_apply_inventory()
            # Post a chatter message with the reason
            if line.reason:
                self.message_post(
                    body=_(
                        '<b>%(product)s</b>: adjusted from %(expected)s to %(counted)s. '
                        'Reason: %(reason)s',
                        product=line.product_id.display_name,
                        expected=line.expected_qty,
                        counted=line.counted_qty,
                        reason=line.reason,
                    )
                )

    # ------------------------------------------------------------------ #
    # Barcode lookup (called from JS)
    # ------------------------------------------------------------------ #
    # def find_line_by_barcode(self, barcode):
    #     """Return the line ID matching a product barcode, or False."""
    #     self.ensure_one()
    #     product = self.env['product.product'].search(
    #         [('barcode', '=', barcode)], limit=1
    #     )
    #     if not product:
    #         return {'error': _('No product found with barcode %s', barcode)}
    #     line = self.line_ids.filtered(lambda l: l.product_id == product)
    #     if not line:
    #         return {'error': _('Product %s is not in this count.', product.display_name)}
    #     return {'line_id': line[0].id, 'product_name': product.display_name}
    def find_line_by_barcode(self, barcode):
        """Return the line ID matching a product barcode using custom barcode lines."""
        self.ensure_one()
        if not barcode:
            return {'error': _('No barcode provided.')}
        # Search in custom barcode lines table
        barcode_line = self.env['product.barcode.line'].search(
            [('name', '=', barcode)], limit=1
        )
        if not barcode_line:
            return {'error': _('No product found with barcode %s', barcode)}
        # Get product.product from product.template
        product = self.env['product.product'].search(
            [('product_tmpl_id', '=', barcode_line.product_id.id)], limit=1
        )
        if not product:
            return {'error': _('No product variant found for barcode %s', barcode)}
        line = self.line_ids.filtered(lambda l: l.product_id == product)
        if not line:
            return {'error': _('Product %s is not in this count.', product.display_name)}
        return {'line_id': line[0].id, 'product_name': product.display_name}
    # ------------------------------------------------------------------ #
    # Report actions
    # ------------------------------------------------------------------ #
    def action_print_count_report(self):
        return self.env.ref(
            'pharmacy_inventory_ops.action_report_pharmacy_count'
        ).report_action(self)

    def action_export_discrepancy_excel(self):
        """Generate XLSX discrepancy report and return as a downloadable binary attachment."""   
        self.ensure_one()
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("You are not authorized to export discrepancy reports."))
        import io, base64
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                'xlsxwriter is required for Excel export. '
                'Install it with: pip install xlsxwriter'
            ))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Discrepancy Report')

        # --- Formats ---
        bold = workbook.add_format({'bold': True, 'bg_color': '#C0392B', 'font_color': '#FFFFFF', 'border': 1})
        normal = workbook.add_format({'border': 1})
        number = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        neg = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'font_color': '#C0392B'})
        pos = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'font_color': '#27AE60'})

        # --- Header info ---
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
        sheet.write(0, 0, 'Discrepancy Report', title_fmt)
        sheet.write(1, 0, f'Reference: {self.name}', workbook.add_format({'bold': True}))
        sheet.write(2, 0, f'Date: {self.count_date}')
        sheet.write(3, 0, f'Responsible: {self.responsible_id.name}')
        sheet.write(4, 0, f'Warehouse: {self.warehouse_id.name if self.warehouse_id else ""}')

        # --- Column headers ---
        headers = ['Internal Ref', 'Product', 'Location', 'Expected Qty',
                'Counted Qty', 'Difference', 'Value of Difference', 'Reason']
        col_widths = [15, 35, 25, 14, 12, 12, 20, 40]
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            sheet.write(6, col, h, bold)
            sheet.set_column(col, col, w)

        # --- Discrepancy lines only ---
        discrepancy_lines = self.line_ids.filtered(
            lambda l: l.counted_status == 'counted' and l.difference != 0
        )

        if not discrepancy_lines:
            sheet.write(8, 0, 'No discrepancies found.', workbook.add_format({'italic': True}))
        else:
            total_value = 0.0
            for row, line in enumerate(discrepancy_lines, start=7):
                diff_fmt = neg if line.difference < 0 else pos
                sheet.write(row, 0, line.product_internal_ref or '', normal)
                sheet.write(row, 1, line.product_id.display_name, normal)
                sheet.write(row, 2, line.location_id.display_name if line.location_id else '', normal)
                sheet.write(row, 3, line.expected_qty, number)
                sheet.write(row, 4, line.counted_qty, number)
                sheet.write(row, 5, line.difference, diff_fmt)
                sheet.write(row, 6, line.difference_value, diff_fmt)
                sheet.write(row, 7, line.reason or '', normal)
                total_value += line.difference_value

            # Totals row
            total_row = 7 + len(discrepancy_lines)
            total_fmt = workbook.add_format({'bold': True, 'border': 1, 'num_format': '#,##0.00'})
            sheet.write(total_row, 5, 'TOTAL', workbook.add_format({'bold': True, 'border': 1}))
            sheet.write(total_row, 6, total_value, total_fmt)

        workbook.close()
        xlsx_data = base64.b64encode(output.getvalue())

        # Save as attachment and return download URL
        attachment = self.env['ir.attachment'].create({
            'name': f'Discrepancy_{self.name.replace("/", "_")}.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_view_discrepancy_lines(self):
        """Smart button → filtered list of discrepancy lines."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Discrepancy Lines'),
            'res_model': 'pharmacy.count.line',
            'view_mode': 'list,form',
            'domain': [
                ('count_id', '=', self.id),
                ('difference', '!=', 0),
            ],
            'context': {'default_count_id': self.id},
        }
    # def action_barcode_scan(self):
    #     self.ensure_one()
    #     if not self.barcode_scan_input:
    #         return
    #     result = self.find_line_by_barcode(self.barcode_scan_input)
    #     self.barcode_scan_input = False
    #     if result.get('error'):
    #         raise UserError(result['error'])
    #     # Highlight the matched line by marking it
    #     line = self.env['pharmacy.count.line'].browse(result['line_id'])
    #     line.is_highlighted = True
    #     # Clear highlight on all other lines
    #     (self.line_ids - line).write({'is_highlighted': False})
    def action_barcode_scan(self):
        self.ensure_one()
        if not self.barcode_scan_input:
            return
        result = self.find_line_by_barcode(self.barcode_scan_input.strip())
        self.barcode_scan_input = False
        if result.get('error'):
            raise UserError(result['error'])
        # Highlight matched line
        line = self.env['pharmacy.count.line'].browse(result['line_id'])
        (self.line_ids - line).write({'is_highlighted': False})
        line.is_highlighted = True
