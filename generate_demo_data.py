"""
Pharmacy Addons Demo Data Generation Script for Odoo 18
------------------------------------------------------
Optimized for: python3 odoo-bin shell -c conf/odoo.conf -d <dbname>
"""

import logging
from datetime import date, timedelta
from odoo import fields

_logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DP = "[DEMO]" # Demo Prefix
USER_PWD = "123"

def safe_ref(env, xml_id):
    try:
        return env.ref(xml_id)
    except:
        return env['uom.uom'].browse()

def create_or_update(env, model, domain, vals):
    """Search for a record by domain; update if found, create if not."""
    record = env[model].search(domain, limit=1)
    if record:
        record.write(vals)
        return record
    # Combine domain and vals for creation
    create_vals = dict(vals)
    for leaf in domain:
        if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[1] == '=':
            create_vals[leaf[0]] = leaf[2]
    return env[model].create(create_vals)

def check_field(env, model, field):
    return field in env[model]._fields

# --- EXECUTION START ---
print(f"--- Starting Demo Data Generation for {env.company.name} ---")

try:
    # 1. SECURITY GROUPS & USERS
    print("Configuring Users...")
    users_to_create = [
        ('demo_pharmacy_mgr', 'Pharmacy Manager', ['pharmacy_base.group_pharmacy_manager']),
        ('demo_pharmacist', 'Pharmacist', ['pharmacy_base.group_pharmacist']),
        ('demo_cashier', 'Cashier', ['pharmacy_base.group_cashier']),
        ('demo_inv_mgr', 'Inventory Manager', ['pharmacy_base.group_inventory_manager']),
        ('demo_purchasing', 'Purchasing Officer', ['pharmacy_base.group_purchasing_officer']),
    ]

    for login, name, groups in users_to_create:
        available_groups = [env.ref('base.group_user').id]
        for g_xml in groups:
            grp = safe_ref(env, g_xml)
            if grp:
                available_groups.append(grp.id)
        
        create_or_update(env, 'res.users', [('login', '=', login)], {
            'name': f"{DP} {name}",
            'password': USER_PWD,
            'groups_id': [(6, 0, available_groups)]
        })

    # 2. PARTNERS (Vendors & Customers)
    print("Configuring Partners...")
    # Vendors
    global_pharma = create_or_update(env, 'res.partner', [('name', '=', f"{DP} Global Pharma")], {
        'is_manufacturer': True if check_field(env, 'res.partner', 'is_manufacturer') else False,
        'is_company': True,
    })
    united_dist = create_or_update(env, 'res.partner', [('name', '=', f"{DP} United Distributors")], {
        'is_company': True,
    })
    cairo_med = create_or_update(env, 'res.partner', [('name', '=', f"{DP} Cairo Medical Co")], {
        'is_manufacturer': True if check_field(env, 'res.partner', 'is_manufacturer') else False,
        'is_company': True,
    })

    # Customers
    customer_ahmed = create_or_update(env, 'res.partner', [('name', '=', f"{DP} Ahmed Hassan")], {
        'phone': '01012345678',
    })
    customer_fatima = create_or_update(env, 'res.partner', [('name', '=', f"{DP} Fatima Zahra")], {
        'phone': '01198765432',
    })
    walk_in = create_or_update(env, 'res.partner', [('name', '=', f"{DP} Walk-in Customer")], {})

    # 3. CATEGORIES
    cat_med = create_or_update(env, 'product.category', [('name', '=', f"{DP} Medicines")], {})
    cat_sup = create_or_update(env, 'product.category', [('name', '=', f"{DP} Supplies")], {})

    # 4. LOCATIONS
    warehouse = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1)
    main_loc = warehouse.lot_stock_id

    # 5. PRODUCTS
    print("Configuring Products...")
    package_uom = env.ref('pharmacy_base.uom_uom_package', raise_if_not_found=False) or env['uom.uom'].search([('name', '=', 'Package')], limit=1)

    # Detect storable field and correct selection value
    storable_vals = {}
    pt = env['product.template']
    if 'is_storable' in pt._fields:
        storable_vals['is_storable'] = True
        storable_vals['type'] = 'consu' # In Odoo 18, is_storable=True makes it storable
    else:
        choices = [s[0] for s in pt._fields['type'].selection]
        if 'storable' in choices:
            storable_vals['type'] = 'storable'
        elif 'product' in choices:
            storable_vals['type'] = 'product'
        else:
            storable_vals['type'] = 'consu'

    def create_demo_product(name, categ, vals):
        p_vals = {
            'categ_id': categ.id,
            'uom_id': package_uom.id,
            'uom_po_id': package_uom.id,
        }
        p_vals.update(storable_vals)
        p_vals.update(vals)
        return create_or_update(env, 'product.template', [('name', '=', f"{DP} {name}")], p_vals)

    # A. Medicines
    amoxicillin = create_demo_product('Amoxicillin 500mg', cat_med, {
        'tracking': 'lot',
        'use_expiration_date': True,
        'public_price': 25.0,
        'standard_price': 18.0,
        'x_classification': 'medicine',
        'generic_name': 'Amoxicillin',
    })
    
    panadol = create_demo_product('Panadol Advance', cat_med, {
        'tracking': 'lot',
        'use_expiration_date': True,
        'public_price': 15.0,
        'standard_price': 10.0,
        'x_classification': 'medicine',
        'generic_name': 'Paracetamol',
    })

    morphine = create_demo_product('Morphine Sulfate', cat_med, {
        'tracking': 'lot',
        'use_expiration_date': True,
        'public_price': 100.0,
        'standard_price': 60.0,
        'x_classification': 'medicine',
        'x_is_scheduled': True,
        'x_schedule_level': 'schedule_2',
    })

    # B. Supplies
    face_mask = create_demo_product('Face Mask (Pack 50)', cat_sup, {
        'tracking': 'none',
        'public_price': 150.0,
        'standard_price': 100.0,
        'x_classification': 'non_medicine',
    })

    sanitizer = create_demo_product('Hand Sanitizer 500ml', cat_sup, {
        'tracking': 'lot',
        'public_price': 60.0,
        'standard_price': 40.0,
        'x_classification': 'non_medicine',
    })

    # 6. STOCK & LOTS
    print("Configuring Stock...")
    expiry_field = 'x_expiry_month_year' if check_field(env, 'stock.lot', 'x_expiry_month_year') else False

    def add_demo_stock(product_tmpl, lot_name, expiry_val, qty):
        variant = product_tmpl.product_variant_id
        lot_domain = [('name', '=', f"{DP}-{lot_name}"), ('product_id', '=', variant.id)]
        lot_vals = {
            'company_id': env.company.id,
            'product_id': variant.id,
        }
        if expiry_field:
            lot_vals[expiry_field] = expiry_val

        lot = create_or_update(env, 'stock.lot', lot_domain, lot_vals)

        quant = env['stock.quant'].with_context(
            inventory_mode=True,
            skip_pharmacy_reason_check=True
        ).create({
            'product_id': variant.id,
            'location_id': main_loc.id,
            'lot_id': lot.id,
            'inventory_quantity': qty,
        })
        if 'inventory_reason' in env['stock.quant']._fields:
            quant.write({'inventory_reason': f'{DP} Initial Stock'})
        quant.action_apply_inventory()
        return lot

    # Normal Stock
    add_demo_stock(amoxicillin, "AMX-101", "06/2027", 200)
    add_demo_stock(panadol, "PAN-202", "12/2026", 500)
    
    # EXPIRED STOCK (for screenshots)
    add_demo_stock(amoxicillin, "AMX-EXP", "01/2024", 15)
    
    # NEAR EXPRY STOCK (for screenshots - orange alert)
    # Using current month or very soon
    near_expiry_val = date.today().strftime("%m/%Y")
    add_demo_stock(panadol, "PAN-NEAR", near_expiry_val, 25)

    add_demo_stock(sanitizer, "SAN-303", "03/2028", 50)

    # 7. PURCHASE ORDERS
    print("Configuring Purchases...")
    # Standard PO
    po_std = create_or_update(env, 'purchase.order', [('origin', '=', f'{DP}-PO-STD')], {
        'partner_id': global_pharma.id,
        'order_line': [
            (0, 0, {
                'product_id': amoxicillin.product_variant_id.id,
                'name': amoxicillin.name,
                'product_qty': 100,
                'price_unit': 17.5,
                'date_planned': fields.Datetime.now(),
            }),
            (0, 0, {
                'product_id': face_mask.product_variant_id.id,
                'name': face_mask.name,
                'product_qty': 20,
                'price_unit': 95.0,
                'date_planned': fields.Datetime.now(),
            }),
        ]
    })

    # Consignment PO
    if check_field(env, 'purchase.order', 'is_consignment'):
        po_cons = create_or_update(env, 'purchase.order', [('origin', '=', f'{DP}-PO-CONS')], {
            'partner_id': united_dist.id,
            'is_consignment': True,
            'order_line': [
                (0, 0, {
                    'product_id': panadol.product_variant_id.id,
                    'name': panadol.name,
                    'product_qty': 300,
                    'price_unit': 9.5,
                    'date_planned': fields.Datetime.now(),
                }),
                (0, 0, {
                    'product_id': sanitizer.product_variant_id.id,
                    'name': sanitizer.name,
                    'product_qty': 100,
                    'price_unit': 38.0,
                    'date_planned': fields.Datetime.now(),
                }),
            ]
        })
        print(f"Consignment PO created: {po_cons.name}")

    # 8. SALES ORDERS
    print("Configuring Sales...")
    so_1 = create_or_update(env, 'sale.order', [('origin', '=', f'{DP}-SO-01')], {
        'partner_id': customer_ahmed.id,
        'order_line': [
            (0, 0, {
                'product_id': panadol.product_variant_id.id,
                'name': panadol.name,
                'product_uom_qty': 2,
                'price_unit': 15.0,
            }),
        ]
    })

    so_2 = create_or_update(env, 'sale.order', [('origin', '=', f'{DP}-SO-02')], {
        'partner_id': customer_fatima.id,
        'order_line': [
            (0, 0, {
                'product_id': amoxicillin.product_variant_id.id,
                'name': amoxicillin.name,
                'product_uom_qty': 5,
                'price_unit': 25.0,
            }),
            (0, 0, {
                'product_id': face_mask.product_variant_id.id,
                'name': face_mask.name,
                'product_uom_qty': 1,
                'price_unit': 150.0,
            }),
        ]
    })

    # 9. PROCUREMENT & WIZARDS (from previous script)
    if env['ir.model'].search([('model', '=', 'pharmacy.shortage.line')]):
        create_or_update(env, 'stock.warehouse.orderpoint', [('product_id', '=', panadol.product_variant_id.id)], {
            'product_min_qty': 500,
            'product_max_qty': 1000,
            'warehouse_id': warehouse.id,
            'location_id': main_loc.id,
        })
        try:
            env['pharmacy.shortage.line'].action_refresh_shortage_lines()
            print("Shortage lines refreshed.")
        except:
            pass

    if env['ir.model'].search([('model', '=', 'pharmacy.wishlist')]):
        nexium = create_demo_product('Nexium 40mg', cat_med, {
            'tracking': 'lot',
            'public_price': 80.0,
            'standard_price': 55.0,
            'x_classification': 'medicine',
        })
        create_or_update(env, 'pharmacy.wishlist', [('product_id', '=', nexium.product_variant_id.id), ('customer_phone', '=', '055555555')], {
            'customer_name': 'Demo Wishlist Customer',
            'quantity': 3,
            'state': 'not_called',
        })
        print("Wishlist entry created.")

    env.cr.commit()
    print("--- Demo Data Generation Successful ---")

except Exception as e:
    env.cr.rollback()
    print(f"!!! Error during generation: {str(e)}")
    import traceback
    traceback.print_exc()
