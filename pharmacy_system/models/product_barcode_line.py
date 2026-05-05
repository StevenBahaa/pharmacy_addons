import random
from odoo import models, fields, api

class ProductBarcodeLine(models.Model):
    _name = 'product.barcode.line'
    _description = 'Product Additional Barcodes'

    product_id = fields.Many2one('product.template', string="Product", ondelete='cascade', index=True)
    name = fields.Char(string="Barcode Value", required=True)
    barcode_type = fields.Selection([
        ('random', 'Internal Random'),
        ('global', 'Global Standard')
    ], string="Type", default='random')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_line_ids = fields.One2many('product.barcode.line', 'product_id', string="Additional Barcodes")

    def action_generate_random_barcode(self):
        for record in self:
            random_base = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            new_barcode = self._generate_ean13_value(random_base)
            self.env['product.barcode.line'].create({
                'name': new_barcode,
                'product_id': record.id,
                'barcode_type': 'random'
            })

    def _generate_ean13_value(self, base):
        if len(base) != 12: return base
        odds = sum(int(base[i]) for i in range(0, 12, 2))
        evens = sum(int(base[i]) for i in range(1, 12, 2))
        total = odds + (evens * 3)
        check_digit = (10 - (total % 10)) % 10
        return f"{base}{check_digit}"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        new_domain = list(domain)
        for condition in domain:
            if isinstance(condition, (list, tuple)) and condition[0] in ('name', 'barcode') and isinstance(condition[2], str):
                search_val = condition[2]
                additional_barcodes = self.env['product.barcode.line'].sudo().search([('name', '=', search_val)])
                if additional_barcodes:
                    product_ids = additional_barcodes.mapped('product_id').ids
                    new_domain = ['|'] + new_domain + [('id', 'in', product_ids)]
                    break
        return super()._search(new_domain, offset=offset, limit=limit, order=order)