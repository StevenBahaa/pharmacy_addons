from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestExpiryCron(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product = cls.env['product.product'].create({
            'name': 'Expiry Cron Test Product',
            'type': 'consu',
            'tracking': 'lot',
            'use_expiration_date': True,
        })

        cls.critical_lot = cls.env['stock.lot'].create({
            'name': 'EXP-CRON-CRITICAL',
            'product_id': cls.product.id,
            'expiration_date': datetime.combine(
                fields.Date.today() + timedelta(days=3),
                datetime.min.time(),
            ),
        })

        cls.normal_lot = cls.env['stock.lot'].create({
            'name': 'EXP-CRON-NORMAL',
            'product_id': cls.product.id,
            'expiration_date': datetime.combine(
                fields.Date.today() + timedelta(days=90),
                datetime.min.time(),
            ),
        })

    def _expiry_alert_activities(self, lot):
        return self.env['mail.activity'].search([
            ('res_id', '=', lot.id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_lot').id),
            ('summary', 'ilike', 'Expiry Alert'),
        ])

    def test_expiry_cron_creates_activity_for_critical_lot(self):
        self.env['stock.lot']._create_expiry_activities()

        critical_activities = self._expiry_alert_activities(self.critical_lot)
        normal_activities = self._expiry_alert_activities(self.normal_lot)

        self.assertEqual(len(critical_activities), 1)
        self.assertFalse(normal_activities)
        self.assertEqual(critical_activities.user_id, self.env.user)

    def test_expiry_cron_does_not_duplicate_activity(self):
        self.env['stock.lot']._create_expiry_activities()
        self.env['stock.lot']._create_expiry_activities()

        self.assertEqual(len(self._expiry_alert_activities(self.critical_lot)), 1)
