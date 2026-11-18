# Architecture

```
React (Vite, :5173) ── /api proxy ──> Django REST (:8000) ──> PostgreSQL
                                          │
                                          ├─ OCR: pypdf (text layer) / Tesseract (images, scanned PDFs)
                                          └─ Inbox providers: Demo (works), Gmail / Graph (interfaces only)
```

## Backend apps (`backend/apps`)
| App | Models | Notes |
|---|---|---|
| accounts | Profile (role admin/staff), CompanyProfile, AuditLog | session login, CSRF, `RoleBasedPermission`, error envelope |
| customers | Customer | unique code, case-insensitive unique name, partial-unique GST |
| materials | Material, MaterialAlias | alias = customer description mapped to a master material |
| inbox | InboxConnection, InboxMessage, InboxAttachment | unique (provider, external_id); attachment SHA-256 checksum for duplicate detection |
| ocr | OCRExtraction | `extracted_data` (machine), `draft_data` (user edits), `verified_data` (final) |
| purchase_orders | PurchaseOrder, PurchaseOrderItem | DB constraints: unique PO number per customer, qty > 0, supplied ≤ ordered |
| supply_tracking | SupplyEntry | qty > 0; the only source of supplied quantity |
| dashboard, reports | – | read-only aggregate queries |

## Key rules
- **Supply is the source of truth.** `PurchaseOrderItem.supplied_quantity` is a cache recomputed with `SUM(SupplyEntry.quantity)` inside the same transaction; PO status (pending / partial / fulfilled) is derived by `purchase_orders.services.derive_status`. Cancelled is a separate action (reopen recomputes from history). Progress % is `supplied / ordered`.
- **Concurrency.** `record_supply/update_supply/delete_supply` lock the PO row (`SELECT … FOR UPDATE`) and validate against the pending balance, so two simultaneous requests cannot both consume the balance. A DB check constraint (`supplied ≤ ordered`) is a second safety net.
- **OCR pipeline.** `extractor.extract_text` → `parser.parse_po_text` (rules + fuzzy customer/material matching, per-field confidence and `ok/uncertain/missing` status) → user edits (`PATCH draft_data`) → `verify` (full PO validation, status *verified*) → `create-po` (transactional; stores attachment, material aliases, links message and extraction).
- **Reports** group quantities by (material, UOM); cancelled POs are excluded from material reports unless filtered explicitly.
- **Security.** Session cookie + `X-CSRFToken`; all endpoints need login; DELETE and settings/user management are Admin-only; secrets only from `.env`.

## Frontend (`frontend/src`)
`api/` Axios client + per-module services · `components/` DataTable, Modal, ConfirmDialog, Toast, LineItemsEditor… · `layouts/AppLayout` · `modules/<module>/` screens named after the module. Lists use server-side pagination/filtering (`hooks/useList`).
