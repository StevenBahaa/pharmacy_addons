# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PharmacyWishlist(models.Model):
    _name = 'pharmacy.wishlist'
    _description = 'Pharmacy Product Wishlist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _check_company_auto = True

    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True, check_company=True)
    quantity = fields.Float(string='Quantity', default=1.0, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, check_company=True)
    customer_name = fields.Char(string='Customer Name', tracking=True)
    customer_phone = fields.Char(string='Customer Phone', required=True, tracking=True)
    customer_unique_code = fields.Char(string='Customer Code', readonly=True, copy=False)
    shop_name = fields.Char(string='Shop/POS Name', readonly=True)
    location_names = fields.Char(string='Available at Locations', readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    note = fields.Text(string='Notes')
    state = fields.Selection([
        ('not_called', 'Waiting for Stock'),
        ('available', 'Ready to Call (Available)'),
        ('called_not_answered', 'Called - No Answer'),
        ('called', 'Fulfilled / Closed'),
    ], string='Status', default='not_called', tracking=True)

    @api.constrains('product_id', 'company_id')
    def _check_out_of_stock(self):
        for record in self:
            # Only check for new records in 'not_called' state
            if record.state == 'not_called':
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id.company_id', '=', record.company_id.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0)
                ])
                if quants:
                    total_qty = sum(quants.mapped('quantity'))
                    raise models.ValidationError(_(
                        "Product '%s' is still in stock (Total: %s) in company %s. "
                        "Wishlist is only for out-of-stock items."
                    ) % (record.product_id.display_name, total_qty, record.company_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
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
                        'pharmacy_customer_code': self.env['ir.sequence'].next_by_code('pharmacy.customer.code'),
                    })
                elif not partner.pharmacy_customer_code:
                    partner.pharmacy_customer_code = self.env['ir.sequence'].next_by_code('pharmacy.customer.code')
                
                vals['partner_id'] = partner.id
                vals['customer_unique_code'] = partner.pharmacy_customer_code
                if not vals.get('customer_name'):
                    vals['customer_name'] = partner.name
        
        return super(PharmacyWishlist, self).create(vals_list)

    def action_set_no_answer(self):
        if not self.env.user.has_group('pharmacy_base.group_cashier') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacist') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("You are not authorized to update wishlist call status."))
        self.write({'state': 'called_not_answered'})
        self._create_followup_activity(_('Customer did not answer. Please try calling again later.'))

    def action_set_called(self):
        if not self.env.user.has_group('pharmacy_base.group_cashier') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacist') and \
           not self.env.user.has_group('pharmacy_base.group_pharmacy_manager'):
            raise UserError(_("You are not authorized to fulfill wishlist requests."))
        self.write({'state': 'called'})
        # Mark existing activities as done
        self.activity_feedback(activity_type_xmlid='mail.mail_activity_data_todo')

    def action_set_available(self, locations=None):
        self.write({
            'state': 'available',
            'location_names': ', '.join(locations) if locations else False
        })
        self._create_followup_activity(_('Product is now available at: %s. Please call the customer.') % (self.location_names or 'Warehouse'))

    def _create_followup_activity(self, summary):
        for record in self:
            record.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=summary,
                user_id=record.user_id.id or self.env.user.id
            )
