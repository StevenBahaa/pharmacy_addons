# UC Coverage Checklist: User Story 4 - Product Configuration & Wishlist

## SC1-UC-02: Shared Barcode
- [x] **ACL**: Barcode lines restricted in Phase 2.
- [x] **Fields**: `barcode_line_ids` protected via ACL corrected in Phase 2.
- [x] **Backend Checks**: `action_generate_random_barcode` guarded in `product_barcode_line.py`.
- [x] **POS Isolation**: POS shared barcode selection logic in JS is read-only (verified by lack of write methods).
- [ ] **Tests**: Negative test for Cashier trying to add shared barcodes.

## SC1-UC-03: Similar & Complementary Products
- [x] **ACL**: Related products restricted in Phase 2.
- [x] **Backend Checks**: `action_make_reciprocal` guarded in `product_related_product.py`.
- [x] **POS Isolation**: POS suggestions panel is read-only for Cashier (verified by lack of write methods in POS model).
- [ ] **Tests**: Verify only Configuration Manager can link products.

## SC5-UC-01: Wishlist
- [x] **ACL**: Wishlist restricted in Phase 2.
- [x] **Record Rules**: Multi-company isolation implemented.
- [x] **Backend Checks**: `action_set_no_answer` and `action_set_called` guarded in `pharmacy_wishlist.py`. `create` handles partner creation safely.
- [x] **POS Isolation**: POS wishlist button triggers `create` which is protected by standard model ACL corrected in Phase 2.
- [ ] **Tests**: Negative test for unauthorized user trying to change wishlist state.