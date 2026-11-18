# PO Tracker — project notes for Claude Code

Supplier purchase-order management: Django REST backend + React (Vite) frontend + PostgreSQL. Currency INR (₹).

## Layout
- `backend/` Django project (`config/`) and apps in `backend/apps/<module>` (accounts, dashboard, customers, materials, inbox, ocr, purchase_orders, supply_tracking, reports). Tests are in `backend/tests/`.
- `frontend/` Vite + React. API layer `src/api/`, shared UI `src/components/`, one folder per module in `src/modules/`.
- `docs/` architecture + API notes. Secrets only in `backend/.env` (never committed; see `.env.example`).

## Commands (Windows / PowerShell)
- Backend venv: `backend\.venv\Scripts\python`. Run: `manage.py runserver`, tests: `manage.py test tests`, seed: `manage.py seed_demo_data`.
- Frontend: `cd frontend; npm run dev` (proxies `/api` to 127.0.0.1:8000), `npm run build`.
- The dev PostgreSQL cluster created for this project lives in `.pgdata/` on port 5433 (`pg_ctl -D .pgdata -o "-p 5433" start`). PostgreSQL is the only supported DB — do not switch to SQLite.

## Rules that must hold
- Supplied quantity is NEVER stored by hand: `PurchaseOrderItem.supplied_quantity` is recalculated from `SupplyEntry` rows and PO status is derived (`purchase_orders/services.py`). All supply writes go through `supply_tracking/services.py` (row locks via `select_for_update`).
- Money/quantities use `DecimalField`; totals and line amounts are computed on the server.
- OCR never invents data: missing fields stay empty with status `missing`. A PO can only be created from an extraction after a user-verified step (`verify` then `create-po`).
- Inbox live providers (Gmail / Microsoft Graph) are interface stubs; never report "Connected" until OAuth is really implemented. Demo emails are flagged `is_demo`.
- API errors use the envelope `{"error": {"code", "status", "message", "details"}}`. Staff cannot DELETE; users/company/inbox config are Admin-only.
- Frontend business data comes from the API only (no hardcoded arrays, no localStorage).
