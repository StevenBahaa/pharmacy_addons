from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PharmacyBulkScrap(models.Model):
    _name = 'pharmacy.bulk.scrap'
    _description = 'Bulk Scrap Session'
    _order = 'date desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    line_ids = fields.One2many('pharmacy.bulk.scrap.line', 'bulk_id', string='Scrap Lines')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Validated')], default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pharmacy.bulk.scrap') or _('New')
        return super(PharmacyBulkScrap, self).create(vals_list)

    def action_validate(self):
        if not self.env.user.has_group('pharmacy_base.group_inventory_manager') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise ValidationError(_("Only Inventory or Pharmacy Managers can validate bulk scrap sessions."))
        for line in self.line_ids:
            available_qty = line.product_id.with_context(location=line.location_id.id).qty_available
            if line.quantity > available_qty:
                raise ValidationError(_("Insufficient stock for %s. Available: %s") % (line.product_id.name, available_qty))

            scrap = self.env['stock.scrap'].create({
                'product_id': line.product_id.id,
                'scrap_qty': line.quantity,
                'lot_id': line.lot_id.id,
                'location_id': line.location_id.id,
                'scrap_location_id': line.scrap_location_id.id,
                'origin': self.name,
            })
            scrap.action_validate()
        self.state = 'done'

class PharmacyBulkScrapLine(models.Model):
    _name = 'pharmacy.bulk.scrap.line'
    _description = 'Bulk Scrap Line'

    bulk_id = fields.Many2one('pharmacy.bulk.scrap')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number')
    quantity = fields.Float(string='Quantity', required=True)
    reason = fields.Text(string='Reason', required=True)
    location_id = fields.Many2one('stock.location', string='Source Location', required=True, domain=[('usage', '=', 'internal')])
    scrap_location_id = fields.Many2one('stock.location', string='Scrap Location', required=True, domain=[('scrap_location', '=', True)])