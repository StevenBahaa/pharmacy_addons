# Pharmacy Addons Security & Roles Documentation

This document explains the security architecture and role-based access control (RBAC) implemented across the Pharmacy Addons suite for Odoo 18.

## Security Architecture

The security model is built on three layers:
1.  **Groups (Roles):** Defined in `pharmacy_base`, these represent functional roles within the pharmacy.
2.  **Access Control Lists (ACLs):** Define model-level permissions (Read, Write, Create, Delete).
3.  **Record Rules:** Implement data isolation (e.g., branch-level or company-level isolation).
4.  **Field-Level Security:** Restricts visibility of sensitive fields (like cost prices or discount data) to specific management roles.

---

## Role Definitions & Capabilities

### 1. Pharmacy Manager
*   **Internal ID:** `pharmacy_base.group_pharmacy_manager`
*   **Description:** The highest authority in the system. Inherits permissions from all other roles.
*   **Key Capabilities:**
    *   Full access to all Pharmacy modules (Purchase, Inventory, Sales, POS, Reports).
    *   Manage system configuration and product settings.
    *   **Price Control:** Can override government price locks and change product categories.
    *   **Audit:** Access to all audit logs and sensitive financial data.
    *   **Operations:** Approve consignment payments and manual inventory adjustments.

### 2. Pharmacist
*   **Internal ID:** `pharmacy_base.group_pharmacist`
*   **Description:** Responsible for clinical operations and medicine dispensing.
*   **Key Capabilities:**
    *   **Clinical:** Manage "Medicine" classified products and view generic names.
    *   **Controlled Substances:** Permission to handle and dispense **Scheduled Medicines** (Schedule I-V).
    *   **Sales:** Can process sales orders and validate prescriptions in the POS.
    *   **Inventory:** View stock levels and expiry dates.

### 3. Inventory Manager
*   **Internal ID:** `pharmacy_base.group_inventory_manager`
*   **Description:** Focuses on stock accuracy, expiry management, and warehouse operations.
*   **Key Capabilities:**
    *   **Expiry Management:** Run expiry detection wizards and manage "Expired Bin" transfers.
    *   **Stock Control:** Perform inventory counts and validate bulk scrap sessions.
    *   **Logistics:** Manage picking operations and internal transfers between locations.
    *   **Reservation:** Access to stock reservation helpers and "force unreserve" actions.

### 4. Purchasing Officer
*   **Internal ID:** `pharmacy_base.group_purchasing_officer`
*   **Description:** Manages supplier relationships and procurement.
*   **Key Capabilities:**
    *   **Procurement:** Create and confirm Purchase Orders (Standard & Consignment).
    *   **Consignment:** Full access to **Consignment Tracking**, including syncing stock lines and triggering vendor bills based on sales.
    *   **Suppliers:** Manage Vendor/Manufacturer records and discount history.
    *   **Shortage List:** Generate POs directly from the pharmacy shortage list.

### 5. Pricing Manager
*   **Internal ID:** `pharmacy_base.group_pricing_manager`
*   **Description:** Specialized role for managing commercial data.
*   **Key Capabilities:**
    *   **Costing:** View and manage `standard_price` (Cost) and Purchase Discount history.
    *   **Pricing:** Update Public Prices (unless locked by government regulation).
    *   **Reporting:** Access to purchasing discount reports and margin analysis.

### 6. Cashier
*   **Internal ID:** `pharmacy_base.group_cashier`
*   **Description:** Front-end staff focused on customer service and POS transactions.
*   **Key Capabilities:**
    *   **POS Operations:** Open/Close POS sessions and process payments.
    *   **Customer CRM:** Create customer profiles and add items to the **Wishlist**.
    *   **Restrictions:** **Cannot** see cost prices, **cannot** change product prices, and **cannot** access backend purchase/inventory configuration.

### 7. Technician
*   **Internal ID:** `pharmacy_base.group_technician`
*   **Description:** Support staff for stock and sales.
*   **Key Capabilities:**
    *   **Stock Visibility:** View product availability and shelf locations.
    *   **Sales Support:** Prepare draft orders or assist in the POS.
    *   **Restrictions:** Limited access to clinical data; cannot dispense scheduled medicines without Pharmacist supervision.

---

## Sensitive Feature Security

### Consignment Workflow (`pharmacy_purchase`)
*   **Marking as Consignment:** Only Purchasing Officers and Managers.
*   **Tracking & Billing:** Requires `group_purchasing_officer`.
*   **Validation:** System prevents generating consignment bills for items not yet sold to customers.

### Medicine Classification (`pharmacy_base`)
*   **Medicine vs Non-Medicine:** Changing a product to "Medicine" automatically triggers Lot tracking and Expiry enforcement.
*   **Scheduled Medicines:** Strictly restricted via `x_is_scheduled` checks in both Backend and POS.

### Expiry Detection (`pharmacy_stock_expiry`)
*   **Transfers:** Moving goods to the "Expired Bin" requires `group_inventory_manager`.
*   **Reporting:** Box prices and total expired values are hidden from low-level roles to protect financial sensitivity.

---

## Data Isolation (Record Rules)
The system implements **Multi-Branch Isolation**. Users assigned to a specific branch/warehouse can only see:
*   Stock levels for their specific location.
*   Purchase/Sales orders originating from their branch.
*   Shortage/Wishlist entries specific to their local customer base.
