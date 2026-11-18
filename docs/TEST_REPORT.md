# Test report (executed 2026-11-17)

| Check | Result |
|---|---|
| `manage.py test tests` (PostgreSQL 18, Python 3.14, Django 6.1) | **40 tests, all passed** (includes real Tesseract 5.4 OCR of a PNG and real PDF text extraction) |
| `manage.py check`, `migrate`, `seed_demo_data` run twice | OK; second seed run created 0 records |
| `npm run build` (Vite 8) | built successfully (chunk-size warning only) |
| Live stack through the Vite proxy (login + CSRF, dashboard, POs, inbox, reports, OCR status) | OK |
| Headless Chrome render of all 10 routes + PO details + OCR verification, logged in as admin | all rendered with data; no JS errors (only the expected pre-login 403 on `/auth/me/`) |

Covered by automated tests: CSRF + session login/logout, Admin/Staff permissions, customer/material CRUD and duplicate/GST validation, delete protection, PO create/edit/filter/delete rules, partial → fulfilled lifecycle, oversupply and zero/negative rejection, ordered-below-supplied rejection, cancel/reopen, overdue, DB constraint safety net, dashboard and report figures updating after supply, CSV export, inbox sync idempotency, simulate → scan → verify → create PO → release, duplicate/reject marks, parser (missing data never fabricated), PDF/PNG upload, unsupported and corrupt files.

Not covered: browser form interactions (click-through of every modal/form), and concurrent-request races (the row-lock design is in place, but no multi-threaded test exists).
