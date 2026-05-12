# Pharmacy Management System for Odoo 18

A professional, modular suite of Odoo 18 Community addons tailored for pharmaceutical retail and inventory management. This project focuses on high-precision stock operations, regulatory compliance, and robust security hardening.

---

## 📖 1. Overview
The **Pharmacy Management System** transforms standard Odoo into a clinical-grade ERP. It addresses specific pharmacy pain points such as controlled substance handling, strict lot expiry workflows, and multi-layered inventory auditing. Designed for modularity, it allows businesses to deploy either the full suite or specific functional blocks.

## ✨ 2. Core Features
*   **Precision Inventory**: Periodic counts, spot-checks, and discrepancy reporting with mandatory reason logging.
*   **Regulatory Safety**: Warnings for scheduled/controlled medicines and automated expiry quarantine.
*   **Advanced Procurement**: Consignment tracking, supplier discount history, and deep PO status visibility.
*   **Retail Intelligence**: Product suggestions at POS, alternate product mapping, and automated low-stock alerts.
*   **Audit Readiness**: Built-in audit logs for sensitive product changes and inventory adjustments.

## 🏗️ 3. Module Structure
The system is built on a hub-and-spoke architecture to ensure clean dependency management:

*   **[pharmacy_base](./pharmacy_base)**: **The Core Engine.** Centralizes all pharmacy security groups (Pharmacist, Technician, Manager), UoM definitions, and foundational product template extensions.
*   **[pharmacy_inventory_ops](./pharmacy_inventory_ops)**: Day-to-day operations including counts, barcode handlers, and stock logs.
*   **[pharmacy_stock_expiry](./pharmacy_stock_expiry)**: Automated lot expiry detection and quarantine location management.
*   **[pharmacy_pos](./pharmacy_pos)**: Specialized retail UI components for clinical warnings and suggestions.
*   **[pharmacy_purchase](./pharmacy_purchase)**: Procurement enhancements for pharmaceutical supply chains.
*   **[pharmacy_inventory_advanced](./pharmacy_inventory_advanced)**: High-level analytics, consumption forecasting, and bulk scrap tools.
*   **[pharmacy_system](./pharmacy_system)**: A metapackage used to install the entire suite and manage global configurations.
*   **Supporting Modules**: `pharmacy_wishlist`, `pharmacy_stock_reservation`, `pharmacy_sales_rules`, and `pharmacy_reports`.

## 🚀 4. Installation
### A. Prerequisites
Ensure the `xlsxwriter` library is installed on your server environment:
```bash
pip install xlsxwriter
```

### B. Deployment
1.  **Add to Path**: Clone this repository into your Odoo `addons` directory.
2.  **Configure**: Add the directory to your `odoo.conf` `addons_path`.
3.  **Update**: Restart Odoo, activate **Developer Mode**, and navigate to **Apps > Update Apps List**.
4.  **Full Install**: Search for `pharmacy_system` and click **Activate**. This will automatically resolve and install all dependencies in the correct sequence.

## 🛡️ 5. Security Model
The suite follows a **Zero-Trust** approach for sensitive operations:
*   **Role-Based Access (RBAC)**: Defined in `pharmacy_base` and strictly enforced across all modules.
*   **Field-Level Security**: Sensitive data (like supplier costs or discount logs) is hidden from front-end users (Cashiers/Technicians).
*   **Record Rules**: Multi-branch isolation ensuring users only see data relevant to their assigned locations.
*   **Backend Validation**: Critical methods (e.g., validating counts or scrapping stock) are protected by explicit group checks.

## 🧪 6. Testing / Validation
The project includes a comprehensive testing suite located in the `/tests` folder of each module:
*   **Unit Tests**: Validate business logic for expiry detection, UoM conversions, and forecast calculations.
*   **Role Testing**: Ensures that restricted groups cannot access unauthorized menus or perform protected actions.
*   **UI Tours**: Automated tours for the POS and Inventory Count wizards to verify front-end stability.
*   **Execution**:
    ```bash
    python3 odoo-bin -c your_config.conf -i pharmacy_system --test-enable --stop-after-init
    ```

## 💻 7. Technical Requirements
*   **Odoo Version**: 18.0 Community Edition.
*   **Python**: 3.10 or higher.
*   **PostgreSQL**: 13.0 or higher.
*   **Dependencies**: `base`, `stock`, `purchase`, `point_of_sale`, `product_expiry`.

## 📝 8. Notes
*   **Configuration**: After installation, visit **Settings > Pharmacy** to configure global parameters.
*   **Permissions**: Ensure the Odoo service user has `read` permissions for all module directories.
*   **Legacy Data**: If migrating from older versions, ensure lot expiry dates are correctly formatted as per Odoo 18 standards.

---
*Developed by Steven Bahaa*
