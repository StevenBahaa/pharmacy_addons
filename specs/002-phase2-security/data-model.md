# Data Model Security Adjustments

No new models are created. We are adjusting ACLs and record rules for existing Phase 2 models.

## Entities (from existing Phase 2 modules)
- `last.purchase.discount`
- `shared.barcode`
- `expired.location`
- `expired.medicine.transfer` (wizard)
- `consignment.tracking`
- `bulk.scrap`
- `shortage.list`
- `pharmacy.wishlist`

## Validation Rules
- All wizards must require `Inventory Manager` or `Pharmacy Manager` group where applicable.
- `write` and `unlink` disabled for history logs (discount history, consignment payment history).