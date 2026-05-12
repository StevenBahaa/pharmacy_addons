# Pharmacy Management System for Odoo 18 Community

A robust, modular ecosystem of Odoo addons designed to handle the complexities of pharmaceutical retail, inventory management, and regulatory compliance.

---

## 📋 1. Overview
The **Pharmacy Management System** is a specialized suite for Odoo 18 Community Edition. It bridges the gap between standard ERP functionality and the stringent requirements of pharmacy operations. Key focus areas include inventory precision (spot-checks and periodic counts), strict lot expiry tracking with automated quarantine, and enhanced POS safety mechanisms for controlled substances.

## ✨ 2. Core Features
* **Precision Inventory Control**: Multi-mode counting (Spot vs. Periodic) with mandatory reason logging for discrepancies.
* **Safety & Compliance**: Integrated warnings for scheduled medicines and automated lot expiry detection.
* **Smart Procurement**: Consignment tracking, supplier discount history, and advanced PO lifecycle visibility.
* **Retail Optimization**: Intelligent product suggestions at the Point of Sale and alternate product mapping.
* **Operational Audit Logging**: Systematic logging of sensitive data changes and stock adjustments.

## 💻 3. Technical Requirements
* **Odoo Version**: 18.0 Community Edition.
* **Python**: 3.10+
* **PostgreSQL**: 14.0+
* **Core Dependencies**: `base`, `stock`, `purchase`, `point_of_sale`, `product_expiry`.

## 🏗️ 4. Module Structure
The system follows a strict **Hub-and-Spoke** dependency model.

> [!IMPORTANT]
> **[pharmacy_base](./pharmacy_base)** is the foundation of the entire suite. It centralizes all pharmacy-specific security groups (Pharmacist, Technician, Manager) and foundational data. **All other feature modules depend on `pharmacy_base`** to ensure consistent access control.

| Module | Purpose | Key Features |
| :--- | :--- | :--- |
| `pharmacy_base` | **Core Hub** | Security groups, Package UoMs, Product extensions. |
| `pharmacy_system` | **Metapackage** | Installs the full suite and manages global settings. |
| `pharmacy_inventory_ops` | Operations | Periodic counts, barcode integration, stock logs. |
| `pharmacy_stock_expiry` | Compliance | Expiry detection cron, quarantine locations. |
| `pharmacy_pos` | Retail UI | Scheduled medicine warnings, product suggestions. |
| `pharmacy_purchase` | Procurement | Consignment tracking, PO tracking, discount history. |
| `pharmacy_inventory_advanced` | Analytics | Consumption forecasting, bulk scrap tools. |
| `pharmacy_reports` | Reporting | Unified PDF/XLSX reporting engine. |
| `pharmacy_wishlist` | CRM | Customer product wishlists and stock alerts. |
| `pharmacy_stock_reservation` | Logistics | Stock reservation for clinical or customer needs. |
| `pharmacy_sales_rules` | Regulation | Pharmaceutical-specific sales restrictions. |

## 🚀 5. Installation
### A. Prerequisites
Ensure your server has the `xlsxwriter` library (required for Excel reporting):
```bash
pip install xlsxwriter
```

### B. Deployment Steps
1. **Clone Repository**: Place this repository in your Odoo `addons_path`.
2. **Server Restart**: Restart the Odoo service to detect new modules.
3. **App Update**: In Odoo (with Developer Mode ON), go to **Apps > Update Apps List**.
4. **Activation**: Search for `pharmacy_system` and click **Activate**. This ensures all dependencies, starting with `pharmacy_base`, are installed in the correct sequence.

## ✅ 6. Post-Installation Configuration Checklist

### 🛠️ General Configuration
- [ ] **Security Groups**: Map users to `Pharmacy / Pharmacist`, `Pharmacy / Technician`, and `Pharmacy / Manager` roles in **Settings > Users**.
- [ ] **Multi-Branch Setup**: Configure Branches and Warehouses to ensure proper data isolation via record rules.

### 📦 Inventory & Expiry
- [ ] **Quarantine Location**: Create or designate a specific location as "Expired" in **Inventory > Configuration > Locations**.
- [ ] **Expiry Detection**: Configure the `Pharmacy: Detection of Expired Lots` cron job frequency (Daily recommended).
- [ ] **Lot Tracking**: Ensure "Lots & Serial Numbers" is enabled in Inventory Settings; verify lot-tracking on high-value products.

### 🛒 Point of Sale (POS)
- [ ] **Safety Warnings**: Flag scheduled medicines in the product template to trigger cashier alerts at checkout.
- [ ] **Shared Barcodes**: Enable and test reciprocal barcode mapping for interchangeable generic brands.

### 💳 Purchase & Procurement
- [ ] **Low-Stock Triggers**: Set reordering rules and verify "Shortage List" automated population.
- [ ] **Vendor Terms**: Configure consignment vendors and link them to designated tracking locations.
- [ ] **Discount History**: Review initial purchase price logs to establish a baseline for discount tracking.

### 🔐 Reporting & Security
- [ ] **Export Permissions**: Restrict XLSX/PDF export capabilities to `Pharmacy / Manager` or higher roles.
- [ ] **Audit Logging**: Verify that changes to sensitive fields (e.g., product prices, stock adjustments) are being captured in **Pharmacy > Configuration > Audit Logs**.
- [ ] **Record Rules**: Test location-based visibility to ensure branch data remains isolated.

### 🧪 Recommended Validation Scenarios
- [ ] **Scenario 1**: Attempt to sell an expired lot (should trigger a POS warning/block).
- [ ] **Scenario 2**: Log in as a `Technician` and attempt to view supplier purchase costs (should be hidden).
- [ ] **Scenario 3**: Run a "Periodic Count" and verify that a discrepancy report generates an audit trail entry.

## 🛡️ 7. Security Model
The suite implements a "Security-First" design:
* **Centralized RBAC**: All roles (Pharmacist, Technician, etc.) are managed in `pharmacy_base`.
* **Multi-Branch Isolation**: Record rules ensure that users only interact with stock and data from their assigned branches.
* **Field-Level Protection**: Sensitive financial data (e.g., product costs) is restricted to management roles.
* **Method Hardening**: Critical backend operations (validation, scrapping) are protected by explicit group checks.

## 🧪 8. Testing / Validation
Each module includes a `tests/` directory covering:
* **Logic Verification**: Unit tests for expiry logic and inventory calculations.
* **Security Validation**: Negative tests ensuring restricted users cannot bypass ACLs.
* **UI Tours**: Automated tours for the POS and Inventory Count workflows.

**Run all tests:**
```bash
python3 odoo-bin -c your_config.conf -i pharmacy_system --test-enable --stop-after-init
```

## 📸 9. Screenshots
*(Placeholders for system visuals)*

### POS Safety Warnings
![POS Warning Placeholder](https://via.placeholder.com/800x400?text=POS+Controlled+Substance+Warning)
*Alert triggered when a scheduled medicine is added to the cart.*

### Expired Medicines Management
![Expired Medicines Placeholder](https://via.placeholder.com/800x400?text=Expired+Medicines+Dashboard)
*Unified view of quarantined stock and upcoming expiries.*

### Consumption Forecast Dashboard
![Forecast Placeholder](https://via.placeholder.com/800x400?text=Inventory+Forecast+Dashboard)
*AI-driven stock level predictions based on historical sales.*

## 📄 10. License
Distributed under the **LGPL-3** License. See `LICENSE` or module manifests for more information.

## 📝 11. Notes
* **Post-Install**: Configure your "Expired" location in **Inventory > Configuration > Locations**.
* **UoM Usage**: Enable "Units of Measure" in Odoo General Settings to utilize pharmacy-specific package units.
* **Auditing**: Access the unified Audit Log via **Pharmacy > Configuration > Audit Logs**.

---
*Developed by Steven Bahaa*
