# PO Tracker

Supplier purchase-order management for a supplier who receives POs from many customer companies: inbox → OCR → verified PO → supply tracking → reports.

**Stack:** Django + Django REST Framework · React (Vite, React Router, Axios, Recharts, Lucide) · PostgreSQL · Tesseract OCR / pypdf / Pillow · session auth with CSRF · INR (₹).

## Prerequisites
Python 3.12+ (built with 3.14), Node 20+, PostgreSQL 14+, Tesseract OCR (`winget install UB-Mannheim.TesseractOCR`).

## First-time setup (PowerShell, from the project root)
```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env        # then edit DB_PASSWORD, DJANGO_SECRET_KEY, DB_PORT, TESSERACT_CMD
# create the database once (psql):  CREATE DATABASE po_tracker;
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser      # this user is an Admin
.venv\Scripts\python manage.py seed_demo_data       # optional, repeatable demo data
cd ..\frontend
npm install
```

## Run
```powershell
# 1. PostgreSQL – use your installed service (default port 5432), or the project-local dev cluster used in development:
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D .pgdata -o "-p 5433" -l .pgdata\server.log start
# 2. Backend  (http://127.0.0.1:8000, Django admin at /admin/, health at /api/v1/health/)
cd backend; .venv\Scripts\python manage.py runserver
# 3. Frontend (http://localhost:5173 – proxies /api to the backend)
cd frontend; npm run dev
```
Sign in with the superuser you created. Staff users are created in **Settings → Users** (Admin only).

## Tests and build
```powershell
cd backend;  .venv\Scripts\python manage.py test tests     # 40 tests (needs PostgreSQL; creates test_po_tracker)
cd frontend; npm run build
```

## Modules
| Module | What it does |
|---|---|
| Dashboard | Live PO counts by status, active/pending value, overdue, recent POs/supplies, customer summary, monthly trend |
| Customers | CRUD, search/filter/pagination, GST/mobile validation, duplicate detection, delete blocked when POs exist (deactivate instead) |
| Materials | CRUD, categories/UOM/default rate, customer-description → material mapping (aliases used by OCR) |
| Inbox | Simulated PO emails in PostgreSQL, Sync Now, simulate email, attachment preview, OCR, verify & convert, mark duplicate/rejected, never imports a message/attachment twice |
| OCR | PDF text-layer extraction, Tesseract for images/scanned PDFs, rule-based parser, side-by-side verification UI, required user verification before PO creation |
| Purchase Orders | CRUD with line items, duplicate PO per customer, filters, cancel/reopen, attachment, supply history |
| Supply Tracking | Record/edit/delete supply per line; no oversupply; status and balances derived from supply rows; row-locked transactions |
| Reports | Customer/material/PO-status/monthly reports, filters, charts, CSV export |
| Settings | Company profile, inbox connection states, OCR status, roles, user management |

## Simulated vs. live
- **Simulated (demo):** the Inbox emails and their PDF/PNG attachments are generated locally and flagged *Demo*. Extraction of those documents is real (pypdf / Tesseract on the generated files).
- **Not live:** Gmail API and Microsoft Graph are provider interfaces only (`backend/apps/inbox/providers.py`). They refuse to sync and the UI shows *Disconnected*. See `docs/EMAIL_INTEGRATION.md` for what is needed to go live.

## Documentation
`docs/ARCHITECTURE.md`, `docs/API.md`, `docs/EMAIL_INTEGRATION.md`, `docs/TEST_REPORT.md`.
