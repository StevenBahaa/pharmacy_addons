# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PharmacyWishlist(models.Model):
    _name = 'pharmacy.wishlist'
    _description = 'Pharmacy Product Wishlist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True)
    quantity = fields.Float(string='Quantity', default=1.0, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    customer_name = fields.Char(string='Customer Name', tracking=True)
    customer_phone = fields.Char(string='Customer Phone', required=True, tracking=True)
    customer_unique_code = fields.Char(related='partner_id.ref', string='Customer Code', readonly=True)
    shop_name = fields.Char(string='Shop/POS Name', readonly=True)
    location_names = fields.Char(string='Available at Locations', readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    note = fields.Text(string='Notes')
    state = fields.Selection([
        ('not_called', 'Not Called'),
        ('available', 'Available'),
        ('no_answer', 'No Answer'),
        ('called', 'Called'),
    ], string='Status', default='not_called', tracking=True)

    @api.model
    def create(self, vals):
        phone = vals.get('customer_phone')
        name = vals.get('customer_name')
        if phone:
            partner = self.env['res.partner'].search([
                '|', ('phone', '=', phone), ('mobile', '=', phone)
            ], limit=1)
            
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': name or f'New Customer ({phone})',
                    'phone': phone,
                    'mobile': phone,
                })
            
            vals['partner_id'] = partner.id
            if not vals.get('customer_name'):
                vals['customer_name'] = partner.name
        
        return super(PharmacyWishlist, self).create(vals)

    def action_set_no_answer(self):
        self.write({'state': 'no_answer'})

    def action_set_called(self):
        self.write({'state': 'called'})
