from odoo import models, fields
from odoo import api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError



class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_expired_location = fields.Boolean(
        string="Expired Location",
        help="Designates a location used to store expired products.",
    )
    expired_label = fields.Char(compute="_compute_expired_label")

    usage = fields.Selection(
        selection_add=[('expired', 'Expired')],
        ondelete={'expired': 'set default'}
    )

    def _compute_expired_label(self):
        for rec in self:
            rec.expired_label = "Expired Location" if rec.is_expired_location else "Not Expired Location"
            
    
    @api.constrains('is_expired_location', 'usage')
    def _check_expired_internal_only(self):
        for loc in self:
            if loc.is_expired_location and loc.usage != 'expired':
                raise ValidationError("Expired location must be expired type.")
            
    def unlink(self):
        for loc in self:
            if loc.is_expired_location:
                raise UserError("Expired Locations cannot be deleted for audit compliance.")
        return super().unlink()
    

    @api.onchange('usage')
    def _onchange_usage_expired(self):
        for rec in self:
            rec.is_expired_location = (rec.usage == 'expired')
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('usage') == 'expired':
                vals['is_expired_location'] = True
        return super().create(vals_list)
    def write(self, vals):
        if 'usage' in vals:
            vals['is_expired_location'] = (vals['usage'] == 'expired')
        return super().write(vals)
    
    def _get_inventory_locations(self):
        locations = super()._get_inventory_locations()

        expired_locations = self.search([('usage', '=', 'expired')])

        return locations | expired_locations