# API (`/api/v1/`)

All endpoints require a logged-in session except `health/`, `auth/csrf/` and `auth/login/`. State-changing requests need the `X-CSRFToken` header (value of the `csrftoken` cookie). Lists are paginated: `?page=&page_size=&search=&ordering=`.

Errors: `{"error": {"code", "status", "message", "details"}}` (400 validation, 403 permission, 404, 409 conflict).

| Area | Endpoints |
|---|---|
| Health | `GET health/` |
| Auth | `GET auth/csrf/` · `POST auth/login/` · `POST auth/logout/` · `GET auth/me/` |
| Users (Admin) | `auth/users/` CRUD · `GET auth/audit-logs/` · `GET/PATCH auth/company/` |
| Customers | `customers/` CRUD (`?is_active=`) |
| Materials | `materials/` CRUD (`?category=&uom=&is_active=`) · `materials/aliases/` CRUD |
| Purchase orders | `purchase-orders/` CRUD (`?customer=&status=&po_date_from=&po_date_to=&delivery_from=&delivery_to=&material=&overdue=&source=`) · `POST …/{id}/cancel/` · `POST …/{id}/reopen/` · `GET/POST …/{id}/attachment/` |
| Supply | `supply-entries/` CRUD (`?po=&item=&customer=&material=&date_from=&date_to=`) |
| Inbox | `inbox/messages/` (list/get) · `POST …/sync/` · `POST …/simulate/` · `POST …/{id}/scan/` · `POST …/{id}/mark/` (`duplicate`/`rejected`/`restore`) · `GET inbox/attachments/{id}/file/` · `inbox/connections/` |
| OCR | `ocr/extractions/` list/get/`PATCH draft_data` · `POST …/upload/` · `POST …/{id}/scan/` · `POST …/{id}/verify/` · `POST …/{id}/create-po/` · `GET …/{id}/file/` · `GET …/engine-status/` |
| Dashboard | `GET dashboard/summary/` |
| Reports | `GET reports/{summary,customers,materials,monthly}/` · `GET reports/po-status/{pending,partial,fulfilled,overdue,cancelled}/` — filters `date_from,date_to,customer,material,status,limit,ordering`; add `export=csv` for CSV |
