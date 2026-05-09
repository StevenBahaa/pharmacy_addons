# Pharmacy Stock Reservation & Transfer Locking
### `pharmacy_stock_reservation` — Odoo 18

---

## Overview

This module implements **INV-UC-04: Stock Reservation & Transfer Locking** for multi-branch pharmacy networks running Odoo 18. It prevents double-shipping by locking inventory the moment a transfer is confirmed, making it unavailable to any other transfer, sale order, or POS session until the lock is explicitly released.

---

## Features

### Core Reservation Engine (`models/stock_quant.py`)
- `pharmacy_reserved_qty` — Float field on `stock.quant`, incremented on confirmation, decremented on cancellation/done.
- `pharmacy_available_qty` — Computed: `quantity − pharmacy_reserved_qty`.
- `_get_available_quantity()` override — All Odoo stock checks (including native `action_assign`) now work against **available** qty, not on-hand.
- `reserve_for_picking(picking)` — Atomically reserves all move lines when a picking is confirmed.
- `release_for_picking(picking)` — Releases all reservations when cancelled, reverted to draft, or validated.

### Transfer Lifecycle Hooks (`models/stock_picking.py`)
| Event | Action |
|---|---|
| `action_confirm()` | Reserve stock for all outgoing moves |
| `action_assign()` | Reserve if not already reserved |
| `action_cancel()` | Release all reservations |
| `action_back_to_draft()` | Release all reservations |
| `button_validate()` | Release all reservations (stock physically moved) |

### Per-line Move Fields (`models/stock_move.py`)
- `pharmacy_reserved_qty` — Total reserved at source for this product/location.
- `pharmacy_available_qty` — Available at source.
- `pharmacy_reservation_status` — `available` / `reserved` / `not_enough`.

### Product Summary (`models/product_product.py`)
- `pharmacy_reserved_qty` and `pharmacy_available_qty` on both `product.product` and `product.template`.
- Displayed as smart buttons: **On Hand | Reserved | Available**.
- Dedicated **Stock Reservation** tab on the product form with explanatory legend.

### POS Integration (`models/pos_order.py`)
- `action_pos_order_paid()` override checks available qty before accepting payment.
- Raises a clear error with on-hand, available, and reserved figures.
- POS session loader includes reservation fields so front-end can display them.

### Force Unreserve (`wizard/force_unreserve_wizard.py`)
- Available only to users in group `pharmacy_inventory_manager`.
- Mandatory reason field (minimum 10 characters).
- Every force-unreserve creates an audit log entry with action type `force_unreserve`.

### Transfer Confirmation Popup (`wizard/transfer_confirm_wizard.py`)
- Opens via **Check Stock Availability** button (visible on Draft outgoing transfers).
- Shows per-line: On Hand / Reserved / Available / Requested / Status.
- Status colours: ✅ Available | ⚠ Partially Reserved | ❌ Not Enough.
- Normal users can only confirm if all lines are `available`.
- Inventory Managers can **Force Confirm** even with insufficient stock.

### Audit Log (`models/reservation_log.py`)
- Model: `pharmacy.reservation.log`
- Every reserve / release / force-unreserve / draft-revert is logged with: product, location, qty, action type, user, timestamp, notes/reason.
- Accessible at **Inventory → Reservations → Reservation Audit Log**.

---

## Installation

1. Copy `pharmacy_stock_reservation/` into your Odoo addons directory.
2. Restart the Odoo service.
3. Go to **Apps**, search for `pharmacy_stock_reservation`, and click **Install**.

### Dependencies
```
stock
purchase
sale_stock
point_of_sale
```

---

## Security Groups

| Group | Inherits | Permissions |
|---|---|---|
| `group_pharmacy_inventory_manager` | `stock.group_stock_manager` | Force unreserve, force-confirm, full audit log write |
| `group_pharmacy_inventory_user` | `stock.group_stock_user` | View reservations, initiate transfers up to available qty |

---

## Field Reference

| Field | Model | Type | Notes |
|---|---|---|---|
| `pharmacy_reserved_qty` | `stock.quant` | Float (stored) | Units committed to confirmed transfers |
| `pharmacy_available_qty` | `stock.quant` | Float (computed) | `quantity − pharmacy_reserved_qty` |
| `pharmacy_reserved_qty` | `product.product` | Float (computed) | Aggregated across all internal locations |
| `pharmacy_available_qty` | `product.product` | Float (computed) | Aggregated across all internal locations |
| `pharmacy_reserved_qty` | `stock.move` | Float (computed) | Reserved at source for this move |
| `pharmacy_available_qty` | `stock.move` | Float (computed) | Available at source for this move |
| `pharmacy_reservation_status` | `stock.move` | Selection (computed) | `available` / `reserved` / `not_enough` |
| `pharmacy_reservation_state` | `stock.picking` | Selection (stored) | `none` / `partial` / `full` / `released` |

---

## Views Modified

| Base View | Change |
|---|---|
| `stock.view_stock_quant_tree` | + Reserved / Available columns |
| `stock.product_open_quants_search` | + "Reserved Stock" filter, "Zero Available" filter |
| `stock.view_stock_quant_form` | + Reserved / Available fields |
| `stock.view_picking_form` | + Reservation state, Check Availability button, Force Unreserve button, per-line columns, Reservation Log tab |
| `stock.vpicktree` | + Reservation state column |
| `product.product_template_form_view` | + Reserved / Available smart buttons, Stock Reservation tab |
| `stock.product_template_tree_view` | + Reserved / Available optional columns |

---

## Error Messages

### Transfer confirmation blocked
```
Cannot confirm transfer WH/OUT/0042.

Product: Amoxicillin 500mg
Requested: 50.00 Units
Available: 30.00 Units
Reserved by: WH/OUT/0039, WH/OUT/0041

Please reduce the quantity or cancel a conflicting transfer.
```

### POS sale blocked
```
Cannot complete POS sale.

Product: Paracetamol 1g tabs
Requested: 100.00
Available: 20.00
Reserved for transfers: 80.00

Please reduce quantity or contact the inventory manager.
```

---

## Module Structure

```
pharmacy_stock_reservation/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── stock_quant.py          # Core reservation engine
│   ├── stock_picking.py        # Lifecycle hooks
│   ├── stock_move.py           # Per-line fields
│   ├── product_product.py      # Product summary fields
│   ├── reservation_log.py      # Audit log model
│   └── pos_order.py            # POS integration
├── wizard/
│   ├── __init__.py
│   ├── force_unreserve_wizard.py
│   ├── force_unreserve_wizard_views.xml
│   ├── transfer_confirm_wizard.py
│   └── transfer_confirm_wizard_views.xml
├── views/
│   ├── stock_quant_views.xml
│   ├── stock_picking_views.xml
│   ├── product_views.xml
│   ├── reservation_log_views.xml
│   └── menu_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── pharmacy_reservation_security.xml
├── data/
│   └── ir_sequence_data.xml
├── report/
│   └── reservation_report_views.xml
└── static/src/
    ├── css/reservation.css
    └── js/reservation_widget.js
```

---

## Notes & Limitations

- Reservation quantities on `stock.quant` are **not** protected by a database-level lock. In very high-concurrency scenarios, add a `SELECT FOR UPDATE` in `_reserve_quantity` if needed.
- The POS `_loader_params_product_product` override requires Odoo 18's POS loader architecture. If your POS version differs, check the method signature.
- The module does **not** touch inter-company transfers; multi-company reservation is out of scope for this version.
