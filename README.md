# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress.** Currently built and working:

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against the
  customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`
- Core models: companies, users, production runs, article costing, contractor
  ledger, expenses
- Command Center KPI + trend endpoints

Not yet built (see `/docs` in the chat history for the full day-by-day roadmap):
department-level waste tracking, receivables/customers, physical inventory,
alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.

# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress — Day 5 of the roadmap complete.**

Day 4-5 (this update):

- Git/CI scaffolding: `scripts/init_repo.sh`, `.github/workflows/backend-ci.yml`, `render.yaml`
- Frontend "hello world" wired to the backend `/health` endpoint (proves the
  deploy pipeline works end to end before real features are built on top)
- Full schema part 1: `Company`, `User`, `Department` (seeded with the
  customer's real 8 departments via `app/db/seed.py`), `Supplier`,
  `RawMaterial`, `Product`
- Hand-written initial Alembic migration (`alembic/versions/0001_initial_schema.py`)
  — see the note in that file about verifying it against autogenerate once
  a real Postgres connection is available

Already built (from Day 2-3/pipeline work):

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against
  the customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`,
  with 4 passing tests in `tests/test_ingestion.py`
- Command Center KPI + trend endpoints

Not yet built: department-level waste tracking (waiting on CEO confirmation —
see open questions in the Day 2-3 audit), receivables/customers, physical
inventory, alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.

# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress — Day 6 of the roadmap complete.**

Day 6 (this update): schema part 2 — `Purchase`, `ProductionBatch`,
`BatchDepartmentStep` (this is the model that makes the 5-stitching-department
requirement real: one row per department a batch passes through, not one
pooled number), and `InventorySnapshot` (deliberately a point-in-time
snapshot, not a running ledger — no real stock-take data exists yet, and a
snapshot only claims to know what was true on one date, nothing invented in
between). Migration `0002_production_detail_schema.py` adds all four tables.

All four start empty for Customer #1 — none of this data existed in his
uploaded file (confirmed in the Day 2-3 audit) — but the schema is ready
the moment purchase records, batch tracking, or a stock count comes in.

Day 4-5:

- Git/CI scaffolding: `scripts/init_repo.sh`, `.github/workflows/backend-ci.yml`, `render.yaml`
- Frontend "hello world" wired to the backend `/health` endpoint (proves the
  deploy pipeline works end to end before real features are built on top)
- Full schema part 1: `Company`, `User`, `Department` (seeded with the
  customer's real 8 departments via `app/db/seed.py`), `Supplier`,
  `RawMaterial`, `Product`
- Hand-written initial Alembic migration (`alembic/versions/0001_initial_schema.py`)
  — see the note in that file about verifying it against autogenerate once
  a real Postgres connection is available

Already built (from Day 2-3/pipeline work):

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against
  the customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`,
  with 4 passing tests in `tests/test_ingestion.py`
- Command Center KPI + trend endpoints

Not yet built: department-level waste tracking (waiting on CEO confirmation —
see open questions in the Day 2-3 audit), receivables/customers, physical
inventory, alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.

# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress — Day 7 of the roadmap complete.**

Day 7 (this update): schema part 3 — `Customer`, `Sale`, `Payment`. This is
the direct answer to "who owes me money" / "overdue payments" — the single
biggest confirmed gap in the customer's data (his file had contractor-payable
data but nothing on the receivable side at all). All three start empty for
Customer #1 until he confirms where his sales/customer records actually live
(open question #3 from the Day 2-3 audit). `Expense` was already built earlier
(from the Balance Sheet ledger pattern found in his real file), so it's not
repeated here. Migration `0003_sales_customers_payments.py` adds the three
new tables.

Day 6:

- Git/CI scaffolding: `scripts/init_repo.sh`, `.github/workflows/backend-ci.yml`, `render.yaml`
- Frontend "hello world" wired to the backend `/health` endpoint (proves the
  deploy pipeline works end to end before real features are built on top)
- Full schema part 1: `Company`, `User`, `Department` (seeded with the
  customer's real 8 departments via `app/db/seed.py`), `Supplier`,
  `RawMaterial`, `Product`
- Hand-written initial Alembic migration (`alembic/versions/0001_initial_schema.py`)
  — see the note in that file about verifying it against autogenerate once
  a real Postgres connection is available

Already built (from Day 2-3/pipeline work):

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against
  the customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`,
  with 4 passing tests in `tests/test_ingestion.py`
- Command Center KPI + trend endpoints

Not yet built: department-level waste tracking (waiting on CEO confirmation —
see open questions in the Day 2-3 audit), receivables/customers, physical
inventory, alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.

# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress — real running dashboard delivered for the CEO demo (ahead of strict Day 8 schema work).**

The CEO confirmed 5 key open questions:

1. Production is **self-made (in-house) only right now** — no active CMT/contractor stream
2. The 5-department model applies to **in-house production**
3. Sales/customers/receivables live in a **separate paper register** (not yet digitized)
4. The old Sheet4 costing data is **confirmed outdated**
5. His real daily production target is **higher than the old "2500/day" note**

Given he wants to see a real running dashboard before handing over new data, `dashboard.html`
(open it directly in a browser) is regenerated from the real sample file through the exact
ingestion engine the backend API uses (`scripts/regenerate_dashboard.py` imports
`backend/app/services/ingestion_service.py` directly — no duplicated logic). It reflects all
5 confirmed answers: CMT/contractor data is labeled historical/legacy, the costing table is
flagged as outdated reference only, and the banner explains sales/purchases/inventory aren't
in it yet because they're still on paper.

**The "swap in a new file and it works" promise is proven, not just claimed:** the regeneration
script was run against a second, structurally different synthetic file (different sheet name,
different column layout) and parsed it correctly with zero code changes.

To regenerate against any new file:

```bash
python scripts/regenerate_dashboard.py path/to/new_file.xlsx
```

Day 7: schema part 3 — `Customer`, `Sale`, `Payment`. This is
the direct answer to "who owes me money" / "overdue payments" — the single
biggest confirmed gap in the customer's data (his file had contractor-payable
data but nothing on the receivable side at all). All three start empty for
Customer #1. `Expense` was already built earlier (from the Balance Sheet
ledger pattern found in his real file), so it's not repeated here. Migration
`0003_sales_customers_payments.py` adds the three new tables.

Day 6:

- Git/CI scaffolding: `scripts/init_repo.sh`, `.github/workflows/backend-ci.yml`, `render.yaml`
- Frontend "hello world" wired to the backend `/health` endpoint (proves the
  deploy pipeline works end to end before real features are built on top)
- Full schema part 1: `Company`, `User`, `Department` (seeded with the
  customer's real 8 departments via `app/db/seed.py`), `Supplier`,
  `RawMaterial`, `Product`
- Hand-written initial Alembic migration (`alembic/versions/0001_initial_schema.py`)
  — see the note in that file about verifying it against autogenerate once
  a real Postgres connection is available

Already built (from Day 2-3/pipeline work):

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against
  the customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`,
  with 4 passing tests in `tests/test_ingestion.py`
- Command Center KPI + trend endpoints

Not yet built: department-level waste tracking (waiting on CEO confirmation —
see open questions in the Day 2-3 audit), receivables/customers, physical
inventory, alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.

# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress — real frontend pages now wired to the real backend (login, signup, upload, live dashboard).**

The static `dashboard.html` demo (built for the CEO before he hands over real data) and the actual
app frontend are now two separate, intentional things:

- `dashboard.html` — a standalone file, no login needed, built from whatever sample file is fed
  into `scripts/regenerate_dashboard.py`. This is what you show him today.
- `frontend/pages/` — the real app: `/login`, `/signup`, `/upload`, `/dashboard`. This is what runs
  once he's a real signed-up customer with his own data in the database.

Closing this out required finishing a gap in the backend first: `dashboard_service.py` had 7
calculation functions (weekly profit, why-analysis, product profitability, lowest-margin product,
expense categories, contractor summary — all ported from the demo script) but only 2 were actually
wired to API endpoints. All 7 now have real endpoints under `/api/dashboard/*`, with matching
Pydantic schemas. Both the standalone demo and the live app now read from the same underlying
logic, no duplicated calculations drifting apart.

Frontend pages share one design system (`frontend/styles/globals.css` — same purple/coral/indigo
palette, Manrope + JetBrains Mono, dark theme toggle) as `dashboard.html`, so the demo and the real
app look and feel identical, not like two different products.

**Honest limitation:** none of this has been run end-to-end (no `npm install`, no live Postgres, no
`uvicorn` boot) — this sandbox has no internet access. Every file was checked for syntax validity
(brace/paren balance for JS, `ast.parse` for Python) but the actual request/response cycle between
frontend and backend is unverified. Before showing this to anyone, run `docker compose up --build`
locally and click through signup → upload → dashboard yourself first.

The CEO confirmed 5 key open questions:

1. Production is **self-made (in-house) only right now** — no active CMT/contractor stream
2. The 5-department model applies to **in-house production**
3. Sales/customers/receivables live in a **separate paper register** (not yet digitized)
4. The old Sheet4 costing data is **confirmed outdated**
5. His real daily production target is **higher than the old "2500/day" note**

Given he wants to see a real running dashboard before handing over new data, `dashboard.html`
(open it directly in a browser) is regenerated from the real sample file through the exact
ingestion engine the backend API uses (`scripts/regenerate_dashboard.py` imports
`backend/app/services/ingestion_service.py` directly — no duplicated logic). It reflects all
5 confirmed answers: CMT/contractor data is labeled historical/legacy, the costing table is
flagged as outdated reference only, and the banner explains sales/purchases/inventory aren't
in it yet because they're still on paper.

**The "swap in a new file and it works" promise is proven, not just claimed:** the regeneration
script was run against a second, structurally different synthetic file (different sheet name,
different column layout) and parsed it correctly with zero code changes.

To regenerate against any new file:

```bash
python scripts/regenerate_dashboard.py path/to/new_file.xlsx
```

Day 7: schema part 3 — `Customer`, `Sale`, `Payment`. This is
the direct answer to "who owes me money" / "overdue payments" — the single
biggest confirmed gap in the customer's data (his file had contractor-payable
data but nothing on the receivable side at all). All three start empty for
Customer #1. `Expense` was already built earlier (from the Balance Sheet
ledger pattern found in his real file), so it's not repeated here. Migration
`0003_sales_customers_payments.py` adds the three new tables.

Day 6:

- Git/CI scaffolding: `scripts/init_repo.sh`, `.github/workflows/backend-ci.yml`, `render.yaml`
- Frontend "hello world" wired to the backend `/health` endpoint (proves the
  deploy pipeline works end to end before real features are built on top)
- Full schema part 1: `Company`, `User`, `Department` (seeded with the
  customer's real 8 departments via `app/db/seed.py`), `Supplier`,
  `RawMaterial`, `Product`
- Hand-written initial Alembic migration (`alembic/versions/0001_initial_schema.py`)
  — see the note in that file about verifying it against autogenerate once
  a real Postgres connection is available

Already built (from Day 2-3/pipeline work):

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against
  the customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`,
  with 4 passing tests in `tests/test_ingestion.py`
- Command Center KPI + trend endpoints

Not yet built: department-level waste tracking (waiting on CEO confirmation —
see open questions in the Day 2-3 audit), receivables/customers, physical
inventory, alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.

# Textile/Garment Business Intelligence Platform

AI-powered business intelligence for textile, apparel, and fashion manufacturers —
starting with one real customer (a garment factory CEO), architected to generalize
into a multi-tenant SaaS product.

## Status

**MVP in progress — deploy-ready for real hosting (Render + Vercel). See `DEPLOYMENT.md` for exact steps.**

The decision here matters: rather than asking the CEO to install Docker Desktop and run terminal
commands on his own laptop (a real support burden for a non-technical user, and a bad demo
experience with `docker compose up` taking a minute the first time), the app is deployed to real
hosting so he just opens a browser link. `render.yaml` (backend) and `frontend/vercel.json`
(frontend) are both configured; `DEPLOYMENT.md` walks through connecting them (they need to know
about each other's URLs, which can't be known until both exist).

The static `dashboard.html` demo (built for the CEO before he hands over real data) and the actual
app frontend are now two separate, intentional things:

- `dashboard.html` — a standalone file, no login needed, built from whatever sample file is fed
  into `scripts/regenerate_dashboard.py`. This is what you show him today.
- `frontend/pages/` — the real app: `/login`, `/signup`, `/upload`, `/dashboard`. This is what runs
  once he's a real signed-up customer with his own data in the database.

Closing this out required finishing a gap in the backend first: `dashboard_service.py` had 7
calculation functions (weekly profit, why-analysis, product profitability, lowest-margin product,
expense categories, contractor summary — all ported from the demo script) but only 2 were actually
wired to API endpoints. All 7 now have real endpoints under `/api/dashboard/*`, with matching
Pydantic schemas. Both the standalone demo and the live app now read from the same underlying
logic, no duplicated calculations drifting apart.

Frontend pages share one design system (`frontend/styles/globals.css` — same purple/coral/indigo
palette, Manrope + JetBrains Mono, dark theme toggle) as `dashboard.html`, so the demo and the real
app look and feel identical, not like two different products.

**Honest limitation:** none of this has been run end-to-end (no `npm install`, no live Postgres, no
`uvicorn` boot) — this sandbox has no internet access. Every file was checked for syntax validity
(brace/paren balance for JS, `ast.parse` for Python) but the actual request/response cycle between
frontend and backend is unverified. Before showing this to anyone, run `docker compose up --build`
locally and click through signup → upload → dashboard yourself first.

The CEO confirmed 5 key open questions:

1. Production is **self-made (in-house) only right now** — no active CMT/contractor stream
2. The 5-department model applies to **in-house production**
3. Sales/customers/receivables live in a **separate paper register** (not yet digitized)
4. The old Sheet4 costing data is **confirmed outdated**
5. His real daily production target is **higher than the old "2500/day" note**

Given he wants to see a real running dashboard before handing over new data, `dashboard.html`
(open it directly in a browser) is regenerated from the real sample file through the exact
ingestion engine the backend API uses (`scripts/regenerate_dashboard.py` imports
`backend/app/services/ingestion_service.py` directly — no duplicated logic). It reflects all
5 confirmed answers: CMT/contractor data is labeled historical/legacy, the costing table is
flagged as outdated reference only, and the banner explains sales/purchases/inventory aren't
in it yet because they're still on paper.

**The "swap in a new file and it works" promise is proven, not just claimed:** the regeneration
script was run against a second, structurally different synthetic file (different sheet name,
different column layout) and parsed it correctly with zero code changes.

To regenerate against any new file:

```bash
python scripts/regenerate_dashboard.py path/to/new_file.xlsx
```

Day 7: schema part 3 — `Customer`, `Sale`, `Payment`. This is
the direct answer to "who owes me money" / "overdue payments" — the single
biggest confirmed gap in the customer's data (his file had contractor-payable
data but nothing on the receivable side at all). All three start empty for
Customer #1. `Expense` was already built earlier (from the Balance Sheet
ledger pattern found in his real file), so it's not repeated here. Migration
`0003_sales_customers_payments.py` adds the three new tables.

Day 6:

- Git/CI scaffolding: `scripts/init_repo.sh`, `.github/workflows/backend-ci.yml`, `render.yaml`
- Frontend "hello world" wired to the backend `/health` endpoint (proves the
  deploy pipeline works end to end before real features are built on top)
- Full schema part 1: `Company`, `User`, `Department` (seeded with the
  customer's real 8 departments via `app/db/seed.py`), `Supplier`,
  `RawMaterial`, `Product`
- Hand-written initial Alembic migration (`alembic/versions/0001_initial_schema.py`)
  — see the note in that file about verifying it against autogenerate once
  a real Postgres connection is available

Already built (from Day 2-3/pipeline work):

- Multi-tenant auth (signup/login, JWT, company-scoped from day one)
- Excel ingestion pipeline (`services/ingestion_service.py`) — validated against
  the customer's real (old, messy) file in `data/sample/Garment_12_updated.xlsx`,
  with 4 passing tests in `tests/test_ingestion.py`
- Command Center KPI + trend endpoints

Not yet built: department-level waste tracking (waiting on CEO confirmation —
see open questions in the Day 2-3 audit), receivables/customers, physical
inventory, alerts, AI Analyst.

## Why the schema looks the way it does

This isn't a generic retail-analytics schema. It reflects what was actually found
auditing the customer's real file:

- He runs **two production streams** — in-house ("Self Made") and outsourced to a
  CMT (Cut-Make-Trim) contractor — tracked with different cost structures. See
  `ProductionRun.stream`.
- His file had **no receivables/customer data at all** — only cost and
  contractor-payable data. That's why there's no `Customer`/`Receivable` model yet;
  building one before knowing where that data actually lives would be guessing.
- **Article-level standard costing** (`Product` model) doubles as the future
  "expected material consumption" baseline for waste detection, because that's
  where the real per-piece cloth-meters figure was found.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then edit JWT_SECRET_KEY at minimum
```

Start Postgres (or use `docker-compose up db` from the repo root), then:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### Try the ingestion pipeline against the sample file

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Demo Garment Co", "email": "ceo@demo.com", "password": "changeme123"}'
# copy the access_token from the response, then:

curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@../data/sample/Garment_12_updated.xlsx"
# review the returned mapping/preview, then POST /api/uploads/{upload_id}/confirm
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up --build
```

## Project layout

See `backend/app/` — `api/` (routes) → `services/` (business logic, reusable and
HTTP-agnostic) → `models/` (SQLAlchemy, every table scoped by `company_id`).
Full rationale in the roadmap doc from the project planning conversation.

## A note on data

`data/sample/` holds the customer's old reference file used to validate the
ingestion pipeline during development. Real, ongoing customer data must never be
committed to this repo — see `.gitignore`.
