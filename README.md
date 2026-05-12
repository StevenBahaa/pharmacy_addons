# Pharmacy Addons for Odoo 18

A comprehensive suite of Odoo 18 Community modules designed for pharmacy management, focusing on inventory precision, security hardening, and specialized retail operations.

## Project Overview

This repository contains a modular pharmacy solution built on Odoo 18. It extends standard Odoo Inventory, Purchase, and POS applications with healthcare-specific requirements such as strict lot expiry management, periodic inventory counts, and controlled substance warnings.

## Core Modules

### 🏥 [Pharmacy Base](./pharmacy_base)
The foundation of the system.
- Shared security groups (Pharmacist, Technician, Inventory Manager, etc.).
- Extended product templates for pharmaceutical data.
- Package Units of Measure (UoM) foundations.

### 📦 [Pharmacy Inventory Operations](./pharmacy_inventory_ops)
Manages the day-to-day stock accuracy.
- **Periodic Counts**: Wizard-driven full inventory counts with category filters.
- **Spot Checks**: Daily quick counts with mandatory reason logging.
- **Barcode Support**: Seamless integration with barcode scanners for counts.
- **Discrepancy Reporting**: PDF and Excel reports for inventory variance.

### ⏳ [Pharmacy Stock Expiry](./pharmacy_stock_expiry)
Strict control over medicine shelf-life.
- Automated expiry detection via cron jobs.
- Dedicated "Expired" locations for quarantined stock.
- Transfer wizards to move expired lots to designated locations.

### 🛒 [Pharmacy POS](./pharmacy_pos)
Enhanced Point of Sale for clinical safety.
- **Scheduled Medicine Warnings**: Popups to alert cashiers about controlled substances.
- **Product Suggestions**: Intelligent suggestions for related products or alternatives.
- **Expiry Integration**: Real-time warnings for expiring lots during sale.

### 💳 [Pharmacy Purchase](./pharmacy_purchase)
Specialized procurement workflows.
- **Discount History**: Tracking price changes and supplier discounts over time.
- **Consignment Tracking**: Manage stock owned by suppliers.
- **PO Tracking**: Advanced visibility into purchase order status and receipt history.

### 📈 [Pharmacy Inventory Advanced](./pharmacy_inventory_advanced)
Advanced stock management and forecasting.
- **Consumption Forecasting**: Predict future needs based on historical sales.
- **Bulk Scrap**: Streamlined interface for mass scrapping of damaged or expired goods.

### 📋 Additional Modules
- **Pharmacy Wishlist**: Customer product wishlists and stock alerts.
- **Pharmacy Stock Reservation**: Reserve stock for specific clinical or customer needs.
- **Pharmacy Sales Rules**: Enforce complex pharmaceutical sales restrictions.
- **Pharmacy Reports**: Specialized reporting suite with XLSX export capabilities.
- **Pharmacy System**: Global configurations and system-wide utilities.

---

## Installation Instructions

Follow these steps to install the full Pharmacy suite.

### 1. Prerequisites
Ensure your environment meets the following requirements:
*   **Odoo Version**: 18.0 Community Edition.
*   **Python**: 3.10 or higher.
*   **Dependencies**: The suite requires the `xlsxwriter` Python library (for Excel reports).
    ```bash
    pip install xlsxwriter
    ```

### 2. Add to Addons Path
1.  Download or clone this repository to your Odoo server.
2.  Add the path of this folder to your `odoo.conf` file:
    ```ini
    [options]
    addons_path = /path/to/odoo/addons, /path/to/pharmacy_addons_repo
    ```

### 3. Update Apps List
1.  Restart your Odoo service.
2.  Log in as **Administrator** and activate **Developer Mode**.
3.  Go to **Apps > Update Apps List** and click **Update**.

### 4. Install Full Suite
1.  Search for **"Pharmacy Management System"** (technical name: `pharmacy_system`) in the Apps menu.
2.  Click **Activate**.
    *   *Note: This will automatically install all sub-modules in the correct dependency order.*

---

## Security & Access Control

The project implements a multi-tier security model including:
- Record rules for branch/location isolation.
- Field-level visibility restrictions (hiding costs from cashiers).
- Backend method protection with explicit group checks.
- Audit logging for sensitive operations.

## Technical Specifications

- **Odoo Version**: 18.0 Community
- **Python**: 3.10+
- **Database**: PostgreSQL
- **Key Dependencies**: `base`, `stock`, `purchase`, `point_of_sale`, `product_expiry`, `report_xlsx`

---
*Developed by Steven Bahaa*
