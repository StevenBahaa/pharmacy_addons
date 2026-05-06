from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields

class TestConsignment(TransactionCase):

    def setUp(self):
        super(TestConsignment, self).setUp()
        self.vendor = self.env['res.partner'].create({'name': 'Consignment Vendor'})
        self.product = self.env['product.product'].create({
            'name': 'Consignment Medicine',
            'type': 'consu',
            'tracking': 'lot',
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def test_01_consignment_flow(self):
        """ Test basic consignment receipt -> sale -> bill """
        # 1. Create Consignment PO
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'is_consignment': True,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 100,
                'product_uom': self.uom_unit.id,
            })]
        })
        po.button_confirm()

        # 2. Receive products with Lot
        picking = po.picking_ids[0]
        lot = self.env['stock.lot'].create({
            'name': 'LOT001',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        
        move = picking.move_ids[0]
        move.move_line_ids.unlink()
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product.id,
            'lot_id': lot.id,
            'quantity': 10,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'picking_id': picking.id,
        })
        picking.button_validate()

        # Check tracking line created
        track_line = self.env['pharmacy.consignment.stock.line'].search([
            ('purchase_order_id', '=', po.id),
            ('lot_id', '=', lot.id)
        ])
        self.assertTrue(track_line, "Tracking line should be created after receipt")
        self.assertEqual(track_line.received_qty, 10)

        # 3. Simulate Sale (Outgoing move)
        customer = self.env['res.partner'].create({'name': 'Customer'})
        picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'owner_id': self.vendor.id,
        })
        move_out = self.env['stock.move'].create({
            'name': 'Sale Move',
            'product_id': self.product.id,
            'product_uom_qty': 5,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': picking_out.location_id.id,
            'location_dest_id': picking_out.location_dest_id.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move_out.id,
            'product_id': self.product.id,
            'lot_id': lot.id,
            'quantity': 5,
            'location_id': move_out.location_id.id,
            'location_dest_id': move_out.location_dest_id.id,
            'picking_id': picking_out.id,
            'owner_id': self.vendor.id,
        })
        picking_out.button_validate()

        self.assertEqual(track_line.sold_qty, 5, "Sold quantity should be updated in tracking line")

        # 4. Use Wizard to create Bill
        wizard = self.env['pharmacy.consignment.track.wizard'].create({
            'purchase_order_id': po.id,
        })
        # Mocking values as they are normally set by action_open_consignment_tracking
        self.env['pharmacy.consignment.track.wizard.line'].create({
            'wizard_id': wizard.id,
            'consignment_stock_line_id': track_line.id,
            'purchase_order_line_id': po.order_line[0].id,
            'product_id': self.product.id,
            'lot_id': lot.id,
            'received_qty': 10,
            'sold_qty': 5,
            'payable_now_qty': 5,
        })
        
        action = wizard.action_create_payment_bill()
        bill = self.env['account.move'].browse(action['res_id'])
        
        self.assertEqual(bill.state, 'draft')
        self.assertEqual(track_line.billed_qty, 0, "Billed quantity should still be 0 as bill is in draft")

        # Check duplicate prevention
        wizard2 = self.env['pharmacy.consignment.track.wizard'].create({'purchase_order_id': po.id})
        # Triggering the logic that usually happens in the action_open...
        po.action_open_consignment_tracking() # This will create another wizard but we check the logic in purchase_order.py
        
        # Test draft bill counts as already processed in logic
        payments = self.env['pharmacy.consignment.payment'].search([
            ('consignment_stock_line_id', '=', track_line.id),
            ('vendor_bill_id.state', '!=', 'cancel')
        ])
        already_processed_qty = sum(payments.mapped('billed_qty'))
        self.assertEqual(already_processed_qty, 5)

        # 5. Post Bill
        bill.action_post()
        self.assertEqual(track_line.billed_qty, 5, "Billed quantity should be 5 after posting")

    def test_02_multiple_pos_different_lots(self):
        """ Test two POs from same vendor/product but different lots """
        # PO 1 - Lot A
        po1 = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'is_consignment': True,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_qty': 10, 'price_unit': 100, 'product_uom': self.uom_unit.id})]
        })
        po1.button_confirm()
        lotA = self.env['stock.lot'].create({'name': 'LOTA', 'product_id': self.product.id, 'company_id': self.env.company.id})
        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]
        move1.move_line_ids.unlink()
        self.env['stock.move.line'].create({'move_id': move1.id, 'product_id': self.product.id, 'lot_id': lotA.id, 'quantity': 10, 'location_id': move1.location_id.id, 'location_dest_id': move1.location_dest_id.id, 'picking_id': picking1.id})
        picking1.button_validate()

        # PO 2 - Lot B
        po2 = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'is_consignment': True,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_qty': 10, 'price_unit': 110, 'product_uom': self.uom_unit.id})]
        })
        po2.button_confirm()
        lotB = self.env['stock.lot'].create({'name': 'LOTB', 'product_id': self.product.id, 'company_id': self.env.company.id})
        picking2 = po2.picking_ids[0]
        move2 = picking2.move_ids[0]
        move2.move_line_ids.unlink()
        self.env['stock.move.line'].create({'move_id': move2.id, 'product_id': self.product.id, 'lot_id': lotB.id, 'quantity': 10, 'location_id': move2.location_id.id, 'location_dest_id': move2.location_dest_id.id, 'picking_id': picking2.id})
        picking2.button_validate()

        # Sale of Lot B
        picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'owner_id': self.vendor.id,
        })
        move_out = self.env['stock.move'].create({
            'name': 'Sale Lot B', 'product_id': self.product.id, 'product_uom_qty': 3, 'product_uom': self.uom_unit.id, 'picking_id': picking_out.id, 'location_id': picking_out.location_id.id, 'location_dest_id': picking_out.location_dest_id.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move_out.id, 'product_id': self.product.id, 'lot_id': lotB.id, 'quantity': 3, 'location_id': move_out.location_id.id, 'location_dest_id': move_out.location_dest_id.id, 'picking_id': picking_out.id, 'owner_id': self.vendor.id,
        })
        picking_out.button_validate()

        track1 = self.env['pharmacy.consignment.stock.line'].search([('purchase_order_id', '=', po1.id)])
        track2 = self.env['pharmacy.consignment.stock.line'].search([('purchase_order_id', '=', po2.id)])

        self.assertEqual(track1.sold_qty, 0, "PO1 should have 0 sold as Lot A wasn't sold")
        self.assertEqual(track2.sold_qty, 3, "PO2 should have 3 sold as Lot B was sold")

    def test_03_return_to_vendor(self):
        """ Test product return to vendor """
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id, 'is_consignment': True,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_qty': 10, 'price_unit': 100, 'product_uom': self.uom_unit.id})]
        })
        po.button_confirm()
        lot = self.env['stock.lot'].create({'name': 'LOTRET', 'product_id': self.product.id, 'company_id': self.env.company.id})
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.move_line_ids.unlink()
        self.env['stock.move.line'].create({'move_id': move.id, 'product_id': self.product.id, 'lot_id': lot.id, 'quantity': 10, 'location_id': move.location_id.id, 'location_dest_id': move.location_dest_id.id, 'picking_id': picking.id})
        picking.button_validate()

        track_line = self.env['pharmacy.consignment.stock.line'].search([('purchase_order_id', '=', po.id)])

        # Return to Vendor
        picking_ret = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.vendor.property_stock_supplier.id,
            'owner_id': self.vendor.id,
        })
        move_ret = self.env['stock.move'].create({
            'name': 'Return Move', 'product_id': self.product.id, 'product_uom_qty': 2, 'product_uom': self.uom_unit.id, 'picking_id': picking_ret.id, 'location_id': picking_ret.location_id.id, 'location_dest_id': picking_ret.location_dest_id.id,
            'purchase_line_id': po.order_line[0].id,
        })
        self.env['stock.move.line'].create({
            'move_id': move_ret.id, 'product_id': self.product.id, 'lot_id': lot.id, 'quantity': 2, 'location_id': move_ret.location_id.id, 'location_dest_id': move_ret.location_dest_id.id, 'picking_id': picking_ret.id, 'owner_id': self.vendor.id,
        })
        picking_ret.button_validate()

        self.assertEqual(track_line.returned_qty, 2)
        self.assertEqual(track_line.remaining_qty, 8)
