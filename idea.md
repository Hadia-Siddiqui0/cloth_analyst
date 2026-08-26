# MASTER PROJECT PROMPT

## Textile & Garment AI Business Intelligence / Operating Intelligence Platform

You are taking over an existing software startup/project. Do NOT treat this as a greenfield project. First understand the business, the existing architecture, the implemented code, and the remaining work. Preserve what already works and extend it carefully.

---

# 1. BUSINESS IDEA

We are building an **AI-powered Business Intelligence and Operating Intelligence platform for textile, apparel, garment, and fashion manufacturers**.

The initial customer is a **garment-factory CEO/owner** who currently relies heavily on:

- Paper registers
- Excel files
- Manually recorded purchases
- Manually recorded sales
- Receivables/payment records
- Production information
- Outdated costing
- Fragmented operational information

The goal is to turn this messy operational data into a single intelligent system.

This is NOT supposed to be just:

- A chatbot
- A dashboard
- An accounting application
- A generic ERP
- An Excel uploader

The product positioning is:

> **Know what happened. Understand why. Predict what’s next. Decide what to do.**

The platform should eventually act as an **AI operating intelligence layer for a manufacturing business**.

---

# 2. THE CORE PROBLEM

A garment factory already generates huge amounts of information, but that information is usually scattered across:

- Paper registers
- Excel spreadsheets
- Different departments
- Purchase records
- Sales records
- Customer records
- Production records
- Inventory records
- Expenses
- Payments/receivables

The CEO should not have to manually combine all of this information to answer questions such as:

- How much did we sell?
- How much money is still receivable?
- Which customers owe us money?
- Which products are profitable?
- What are our biggest costs?
- Which raw materials are being consumed?
- What happened to profitability?
- Why did profit decrease?
- Which department/process is causing delays?
- What should we prioritize?
- What might happen next?
- What action should management take?

The platform should collect the information, normalize it, calculate reliable metrics, visualize it, and eventually use AI/analytics to explain and predict business outcomes.

---

# 3. TARGET CUSTOMER

Initial target:

**One garment-factory CEO/owner.**

However, the architecture must be designed as a **multi-tenant SaaS platform** so that multiple companies can eventually use the system while their data remains strictly isolated.

Do not hard-code the application around only one company.

Every company's data must remain securely separated.

---

# 4. CORE DATA SOURCES

The factory currently has two especially important types of data:

### A. Paper registers

Important registers include:

- Purchases
- Sales
- Receivables
- Other operational records

The system should eventually allow the user to photograph/scan these registers and extract structured information using OCR.

### B. Existing Excel/CSV data

The factory has old and messy Excel files.

These files may:

- Have different column names
- Have different column orders
- Contain different formats
- Have missing columns
- Have extra columns
- Contain inconsistent values
- Represent the same business concept in different ways

Therefore, Excel/CSV ingestion must be **universal and intelligent**, rather than depending on one exact spreadsheet format.

The system should:

1. Accept XLSX/CSV files.
2. Inspect their structure.
3. Identify columns.
4. Map columns to the platform's internal schema.
5. Validate values.
6. Detect missing/invalid data.
7. Show problems to the user.
8. Allow manual correction/mapping when necessary.
9. Import valid data safely.
10. Never silently create incorrect business data.

---

# 5. OCR / REGISTER PHOTO SYSTEM

A major feature is allowing factory users to photograph paper registers.

The intended flow is approximately:

PHOTO/UPLOAD REGISTER
↓
IMAGE PROCESSING
↓
OCR
↓
TABLE/ROW/COLUMN DETECTION
↓
FIELD EXTRACTION
↓
NORMALIZATION
↓
VALIDATION
↓
USER REVIEW
↓
CONFIRM
↓
DATABASE

OCR should NOT blindly insert extracted values into the database.

The system must provide a review/verification step because OCR can make mistakes.

The product must never pretend that uncertain OCR information is definitely correct.

OCR/register-photo functionality was still in progress and needs to be completed.

---

# 6. IMPORTANT BUSINESS ENTITIES

The backend already has models/migrations for:

- Company
- User
- Department
- Supplier
- RawMaterial
- Product
- Purchase
- ProductionBatch
- BatchDepartmentStep
- InventorySnapshot
- Customer
- Sale
- Payment
- Expense

These existing models should be preserved unless there is a genuine architectural reason to modify them.

Do not unnecessarily redesign the database.

---

# 7. BUSINESS LOGIC

The platform needs reliable business calculations.

For example:

### Revenue

Revenue should be calculated from recorded sales:

SUM(sales.amount)

### Profit

At the current stage:

Profit = Revenue − Recorded Costs

Do NOT invent costs or pretend that a profitability number is complete if the required cost data has not actually been recorded.

The system must clearly distinguish:

- Recorded data
- Calculated metrics
- Estimates
- Predictions
- Recommendations

If the data is insufficient for a prediction or recommendation, the product should say so.

Never manufacture certainty.

---

# 8. AI PHILOSOPHY

AI is NOT simply a chatbot placed on top of a dashboard.

The long-term product should answer four levels of management intelligence:

### LEVEL 1 — WHAT HAPPENED?

Examples:

- Sales increased/decreased.
- Expenses increased.
- Receivables increased.
- A product generated X revenue.
- A customer has outstanding payments.

### LEVEL 2 — WHY DID IT HAPPEN?

Examples:

- Revenue decreased because sales of a specific product declined.
- Profit decreased because recorded costs increased.
- Receivables increased because outstanding customer payments increased.

### LEVEL 3 — WHAT WILL HAPPEN?

Eventually introduce forecasting/prediction for things such as:

- Sales
- Demand
- Cash flow
- Inventory
- Production
- Receivables
- Potential operational problems

Predictions must always state their data basis and must not be presented as guaranteed outcomes.

### LEVEL 4 — WHAT SHOULD WE DO?

Eventually provide actionable recommendations.

Examples:

- Follow up with customers with high outstanding receivables.
- Investigate unusually high costs.
- Review products whose profitability is deteriorating.
- Investigate production bottlenecks.
- Replenish materials when appropriate.

Recommendations must be based on actual available data.

---

# 9. CURRENT TECH STACK — LOCKED

Do NOT replace the architecture with another framework unless explicitly instructed.

## Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## Frontend

- React / Next.js

## Authentication

- Hand-built JWT authentication
- bcrypt password hashing

## Deployment

Backend:

- Render

Frontend:

- Vercel

The architecture should remain clean, modular, secure, and scalable.

---

# 10. MULTI-TENANCY

Although the MVP starts with one garment-factory CEO, the architecture is intended for multi-tenant SaaS.

A company/tenant must only be able to access its own data.

Every relevant business record must be associated correctly with the company/tenant.

Security must be treated as a first-class requirement.

Never rely solely on frontend restrictions for tenant isolation.

The backend must enforce authorization and tenant boundaries.

---

# 11. AUTHENTICATION

Authentication has already been implemented around:

- Signup
- Login
- JWT
- bcrypt

Existing authentication should be preserved.

However, authentication/security hardening and full RBAC verification still need attention.

Eventually the platform should support appropriate roles/permissions, rather than allowing every authenticated user unrestricted access.

---

# 12. CURRENT FRONTEND

A real frontend/dashboard has already been connected to the backend.

Current pages include:

- `/login`
- `/signup`
- `/upload`
- `/dashboard`

There is also a standalone `dashboard.html` that shares dashboard logic/design.

The dashboard is not just a static mockup anymore.

It is connected to the real backend.

---

# 13. CURRENT BACKEND/DASHBOARD WORK

Dashboard services have already been implemented with **seven analytics endpoints**.

The frontend consumes backend data to display real business information.

Do not replace the working dashboard with fake/static data.

Whenever possible, use real API/database data.

---

# 14. DATA INGESTION WORK ALREADY DONE

Real sample-file ingestion has been tested.

The system has also been tested with structurally different synthetic Excel data to verify that the ingestion system is not dependent on one exact spreadsheet structure.

This is important.

The goal is a robust ingestion system capable of handling messy real-world factory data.

Do not regress this functionality.

---

# 15. CURRENT PRODUCT STATE

The project has progressed beyond an idea/prototype.

Current state:

### Already implemented

- Backend architecture
- FastAPI backend
- PostgreSQL integration
- SQLAlchemy models
- Alembic migrations
- Company model
- User model
- Department model
- Supplier model
- Raw material model
- Product model
- Purchase model
- Production batch model
- Batch department step model
- Inventory snapshot model
- Customer model
- Sale model
- Payment model
- Expense model
- Authentication foundation
- Signup
- Login
- JWT authentication
- bcrypt password hashing
- Dashboard APIs
- Seven analytics endpoints
- React/Next.js frontend
- Login page
- Signup page
- Upload page
- Dashboard page
- Backend/frontend integration
- Real sample-file ingestion
- Structurally different synthetic-file ingestion testing
- Backend deployed on Render
- Frontend deployed on Vercel

---

# 16. WORK CURRENTLY IN PROGRESS / REMAINING

The following areas still need to be completed or strengthened:

## HIGH PRIORITY

### 1. OCR / Register Photo

Complete the paper-register photo workflow:

Photo → OCR → extraction → normalization → validation → user review → database.

Do not bypass review.

---

### 2. Waste Tracking

Add proper manufacturing waste tracking.

The system should eventually understand:

- Material used
- Expected usage
- Actual usage
- Waste
- Waste percentage
- Potential abnormal waste

This should eventually feed analytics and AI explanations.

---

### 3. Physical Inventory Flows

Build proper physical inventory workflows.

The system needs to distinguish between:

- Recorded inventory
- Physical inventory
- Inventory snapshots
- Variances

Do not assume the database quantity is automatically equal to the physically available quantity.

---

### 4. Alerts

Introduce useful operational alerts.

Potential areas include:

- High receivables
- Unusual expenses
- Inventory issues
- Production delays
- Abnormal waste
- Other data-supported anomalies

Alerts should be based on actual business data.

---

### 5. RBAC / SECURITY

Complete and verify:

- Role-based access control
- Authorization
- Tenant isolation
- JWT handling
- Password security
- Backend authorization
- API protection

Do not consider frontend hiding of UI elements to be security.

---

### 6. AI / PREDICTIONS

After the underlying data is reliable, build:

- Business explanations
- Trend analysis
- Forecasting
- Anomaly detection
- Recommendations

Do not build flashy AI features that operate on unreliable or incomplete data.

---

### 7. END-TO-END TESTING

The complete runtime flow still needs proper verification.

Test:

Signup
→ Login
→ Authentication
→ Upload
→ Ingestion
→ Database
→ Analytics APIs
→ Dashboard
→ OCR flow
→ Business calculations
→ Tenant isolation
→ Authorization

Do not assume something works simply because the code exists.

---

# 17. DEVELOPMENT RULES

When working on this project:

### Rule 1 — Inspect before changing

Before modifying anything:

- Inspect the repository.
- Understand the existing architecture.
- Find the relevant backend/frontend files.
- Understand database models.
- Understand existing APIs.
- Understand existing authentication.
- Understand current ingestion logic.

Do not blindly overwrite existing code.

---

### Rule 2 — Preserve working functionality

This is an existing project.

Do not rewrite working components merely for stylistic reasons.

Avoid unnecessary architectural changes.

---

### Rule 3 — No fake data in production functionality

Mock data can be used for development/testing when explicitly appropriate.

But production dashboard/business calculations must come from actual backend/database data.

---

### Rule 4 — Never invent business facts

If data does not exist, say that it does not exist.

For example:

Bad:

> "Your profit will increase by 18%."

Better:

> "Based on the available historical data, the model estimates..."

And if insufficient data exists:

> "There is not enough recorded data to make a reliable prediction."

---

### Rule 5 — Calculations must be traceable

Important numbers should ultimately be explainable back to source records.

For example:

Revenue
→ Sales records
→ Sale amount

Profit
→ Revenue
→ Recorded costs
→ Calculation

Do not hide unexplained calculations inside the UI.

---

### Rule 6 — Backend is the source of truth

Business calculations, permissions, validation, and tenant isolation belong on the backend.

The frontend should not be trusted to enforce business rules.

---

### Rule 7 — Database migrations

Whenever database structure changes:

- Update SQLAlchemy models appropriately.
- Create an Alembic migration.
- Test the migration.
- Ensure existing data is not unnecessarily destroyed.

Never casually drop production data.

---

# 18. PRODUCT VISION

The eventual product should feel like an intelligent operating system for a garment manufacturer.

A CEO should be able to open the system and quickly understand:

## BUSINESS HEALTH

- Revenue
- Costs
- Profit
- Receivables
- Expenses
- Inventory
- Production

## OPERATIONAL HEALTH

- Production progress
- Department performance
- Material consumption
- Waste
- Inventory variance
- Delays

## CUSTOMER HEALTH

- Sales
- Outstanding payments
- Customer contribution
- Payment behavior

## AI INTELLIGENCE

- What changed?
- Why did it change?
- What is likely to happen?
- What should management do?

---

# 19. EXAMPLE FUTURE CEO EXPERIENCE

The CEO uploads an old Excel file.

The platform recognizes:

- Customer
- Product
- Sale amount
- Date
- Payment
- Other relevant fields

The platform validates the data.

The CEO reviews any uncertain mappings.

The data is imported.

The dashboard updates.

The system then says something like:

> Sales increased compared with the previous period.

Then:

> The increase was primarily driven by Product X and Customer Y.

Then:

> Outstanding receivables also increased.

Then eventually:

> Based on historical payment behavior, several customers may require follow-up.

The CEO can then investigate the underlying records.

This is the experience we are building.

---

# 20. IMPORTANT PRODUCT PRINCIPLE

The platform must progress through this hierarchy:

RAW DATA
↓
CLEAN DATA
↓
RELIABLE METRICS
↓
BUSINESS INSIGHTS
↓
EXPLANATIONS
↓
PREDICTIONS
↓
RECOMMENDATIONS
↓
DECISIONS

Do NOT jump directly from messy Excel/PDF/photos to AI recommendations without establishing reliable data first.

---

# 21. WHAT I EXPECT FROM YOU AS THE CODING AI

You are now the engineering agent responsible for continuing this existing project.

Before making changes:

1. Inspect the entire repository structure.
2. Identify backend and frontend architecture.
3. Identify database models.
4. Identify migrations.
5. Identify authentication implementation.
6. Identify current ingestion system.
7. Identify dashboard endpoints.
8. Identify current OCR implementation.
9. Identify deployment configuration.
10. Identify unfinished functionality.

Then produce a concise assessment:

### ALREADY WORKING

What is actually implemented.

### BROKEN

What currently fails.

### INCOMPLETE

What exists but is unfinished.

### MISSING

What has not been implemented.

### NEXT PRIORITY

What should be completed first.

Do not claim something works until you actually verify it.

---

# 22. CURRENT PRIORITY ORDER

Unless the repository reveals a blocking issue, prioritize work approximately in this order:

1. Inspect and understand the existing implementation.
2. Verify database/business calculations.
3. Complete inventory and physical inventory flows.
4. Add waste tracking.
5. Complete alerts.
6. Harden authentication/RBAC/tenant isolation.
7. Perform full end-to-end testing.
8. Build reliable AI analytics/predictions.
9. Build recommendation/decision intelligence.

---

# 23. FINAL PRODUCT DEFINITION

This startup is ultimately:

> **An AI-powered operating intelligence platform for textile and garment manufacturers that converts fragmented paper records, Excel data, operational records, sales, purchases, production, inventory, payments, expenses, and other business information into reliable business intelligence, explanations, predictions, and actionable decisions.**

It should help a factory CEO move from:

**"I have a lot of records but don't know what is happening."**

to:

**"I know what happened, why it happened, what is likely to happen next, and what I should do about it."**

The architecture starts with one garment factory but must be capable of becoming a secure multi-tenant SaaS product.

The technology stack is locked:

**FastAPI + Python + PostgreSQL + SQLAlchemy/Alembic + React/Next.js + JWT/bcrypt**

Backend deployment:

**Render**

Frontend deployment:

**Vercel**

The existing implementation must be preserved and improved rather than unnecessarily rewritten.

# END OF MASTER PROMPT
