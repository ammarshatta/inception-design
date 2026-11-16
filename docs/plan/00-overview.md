# Overview

## Decision

Build Inceptiondesign on **ERPNext v16** with one custom Frappe app, **`construction_core`**.

- **Phases 0–18:** the whole platform is built and tested on the owner's computer, at no cost.
- **Phase 19 (launch):** it moves to a hosted server outside the office, and goes live. See `hosting-options.md`.

### Why ERPNext (re-checked November 2026)

| Option | Verdict |
|---|---|
| **ERPNext v16 + custom app** | **Chosen.** Gives us, free (GPLv3): <br>• full accounting, invoices, payments, suppliers, items, leads and projects <br>• login (including Google and Facebook), roles and permissions <br>• file uploads, email and realtime <br>We build only the construction-specific parts. |
| Odoo Community | Free edition has limited accounting; full accounting is in the paid Enterprise edition, priced per user. |
| Next.js + Supabase | Supabase gives auth, database and storage, but accounting would have to be built from scratch. The free tier pauses after a week of inactivity and has 1 GB of file storage, so production means Pro at $25/month. Also, ERPNext v16 does not support PostgreSQL. |
| Payload CMS on Cloudflare | Cheapest to host, but no accounting. Same problem as Supabase. |
| Existing construction apps on Frappe | None covers our client portal and photo tracking. <br>• **BuildSuite** core is still beta. <br>• **Quantbit BuildX** (repo `QuantbitERP/Quantbit-Construction-Management`, presented August 2026) has BOQ, site reports and contracts, but it is India-focused and has no stated license. <br>We keep both as references for the estimating phase (7), not as dependencies. |

## Architecture

One Frappe site serves three areas on one domain, with one login session and no separate API server:

| Path | Who | Built with |
|---|---|---|
| `/`, `/designs`, `/projects`, `/p/<token>`, `/privacy`, `/data-deletion` | Visitors | Frappe website pages (Jinja) in `construction_core/www` |
| `/portal` | Clients and engineers | Vue 3 + frappe-ui SPA in `construction_core/frontend` |
| `/app` | Admin and accountant | ERPNext desk + a "المقاولات" workspace |

Optional later: **Frappe Builder** (MIT) for marketing pages the owner edits visually. It is not needed for v1.

## Roles

| Person | Frappe roles | Uses | Can access |
|---|---|---|---|
| Admin (office owner) | System Manager, Construction Admin | `/app` | Everything |
| Accountant | Accounts User, Accounts Manager | `/app` | Invoices, payments, expenses, reports |
| Engineer | Construction Engineer (System User) | `/portal` | Projects where they are in `Project User` only |
| Client | Construction Client (Website User) | `/portal` | Their own projects; never anything `internal_only` |
| Visitor | Guest | Public pages | Published designs and published projects, through allowlist functions only |
| Sales (phase 7) | Construction Sales | `/app` | Leads, opportunities, estimates; no accounting |
| Foreman (phase 11) | Construction Foreman (System User) | `/portal` | Their crew's assignments, daily logs and clock-in for assigned projects |
| Subcontractor (optional, phase 13) | Supplier (ERPNext Supplier Portal) | `/supplier-portal` | Their own orders and invoices only |

## Data model

### Reused from ERPNext

- `Customer`, `Contact`, `User`, `Lead`
- `Project` with its `Project User` child table, and `Task`
- `Sales Invoice`, `Payment Entry`, `Purchase Invoice`, `Supplier`
- `Item`, `Item Price`, `File`

### Custom fields

- **`Project`:**
  - `slug`
  - `visibility` (Select: private / link / public)
  - `share_token_hash`, `share_expires_at`
  - `public_show_stages` (Check)
  - `public_show_photos` (Select: none / publishable / all)
  - `public_show_updates_text` (Check)
  - `public_location_level` (Select: area / full)
  - `public_show_client_name` (Check)
  - `area_label`
  - `phase_template` (Link)
  - `weighted_progress` (Percent, read only)
- **`User`:** `must_change_password` (Check)
- **`Purchase Invoice`:** `project_stage` (Link)
- **`Lead`:** `design_template` (Link), `apartment_area_m2` (Float), `governorate` (Data)

### New DocTypes in `construction_core`

| DocType | Type | Key fields |
|---|---|---|
| `Phase Template` | normal | template_name, stages (table: `Phase Template Stage`) |
| `Phase Template Stage` | child | stage_name, weight, checklist_text (one item per line) |
| `Project Stage` | normal | project, stage_name, sort_order, weight, planned_start, planned_end, actual_start, actual_end, status (Not Started / In Progress / On Hold / Done), progress, progress_mode (Auto / Manual), checklist (table: `Stage Checklist Item`) |
| `Stage Checklist Item` | child | label, done, done_by, done_on |
| `Stage Update` | normal | project, project_stage, text, progress_after, internal_only, media (table: `Stage Update Media`) |
| `Stage Update Media` | child | file (Attach), kind (Photo / Video), publishable, public_file, taken_at |
| `Payment Milestone` | normal | project, project_stage, label, amount (Currency), status (Upcoming / Due / Invoiced / Paid), sales_invoice |
| `Project Message` | normal | project, kind (Text / Approval), text, attachment, approval_title, approval_detail, approval_amount, approval_status (Pending / Approved / Question), answered_on, answered_by |
| `Design Template` | normal | title, slug, description, area_m2, bedrooms, bathrooms, style, cost_from, cost_to, duration_weeks, phase_template, published, cover, media (table: `Design Media`) |
| `Design Media` | child | file, kind (3D / Room / Floor Plan / Execution), caption |
| `Inceptiondesign Settings` | single | office display name, logo, colors, WhatsApp number, terms text, default engineer, and feature flags (selections, gps_clock_in, online_payments, ai_assistant, public_catalog) |

A stage's progress `status` and the client's approval are separate things:
- Approvals are `Project Message` records of kind Approval.
- Once answered, an approval is immutable for everyone, including the admin.

## Calculations

- **Stage progress (Auto):** done checklist items ÷ all items × 100. In Manual mode, the engineer enters it.
- **Project progress:** Σ(weight × progress) ÷ Σ(weight). The desk shows a warning when the weights do not add up to 100.
- **Template copy:** creating a project from a template copies its stages and checklists into `Project Stage` records. Later template edits never change existing projects.

## Repository layout

The git repo (GitHub: `inceptiondesign`) is the app folder itself, `frappe-bench/apps/construction_core/`:

```text
construction_core/                     repo root = Frappe app root
  CLAUDE.md
  pyproject.toml
  construction_core/                   Python package
    construction_core/doctype/         our DocTypes (module "Construction Core")
    api/public.py                      the only place with allow_guest=True
    api/portal.py                      portal methods (login required)
    permissions.py
    www/                               public pages
    templates/  public/  fixtures/  patches/  tests/
    hooks.py
  frontend/                            Vue 3 + frappe-ui portal
  deploy/                              apps.json, compose overrides, backup.sh, deploy.sh (phase 19)
  docs/
    plan/        this plan
    progress/    phase reports written by the agent
    versions.md
```

## Phases

| # | File | What | Where |
|---|---|---|---|
| 0 | `phase-00-foundation.md` | App, portal skeleton, CI | Local |
| 1 | `phase-01-data-permissions.md` | Core DocTypes and project permissions | Local |
| 2 | `phase-02-admin-onboarding.md` | Admin screens, client onboarding | Local |
| 3 | `phase-03-engineer-portal.md` | Engineer portal, photo uploads | Local |
| 4 | `phase-04-client-portal.md` | Client portal, chat, approvals | Local |
| 5 | `phase-05-public-pages.md` | Design catalog, public projects, lead form | Local |
| 6 | `phase-06-money.md` | Milestone invoices, collections, expenses | Local |
| 7 | `phase-07-sales-estimating.md` | Pipeline, price library, costing engine, estimates | Local |
| 8 | `phase-08-proposals-esign.md` | Proposals, e-signature, project kickoff | Local |
| 9 | `phase-09-selections.md` | Finish selections | Local |
| 10 | `phase-10-change-orders.md` | Change orders | Local |
| 11 | `phase-11-scheduling-crews.md` | Gantt, calendar, crews, conflicts | Local |
| 12 | `phase-12-daily-logs-time.md` | Daily logs, timesheets, GPS clock-in | Local |
| 13 | `phase-13-subcontractors-procurement.md` | Purchasing, subcontracts, progress claims | Local |
| 14 | `phase-14-documents-markup-takeoff.md` | Documents, photo markup, takeoff | Local |
| 15 | `phase-15-online-payments-reminders.md` | Online payments (sandbox), reminders | Local |
| 16 | `phase-16-offline-mobile-push.md` | Offline PWA, push notifications | Local |
| 17 | `phase-17-reports-dashboards.md` | WIP, job costing, dashboards | Local |
| 18 | `phase-18-ai-assistant.md` | AI assistant, MCP connector | Local |
| 19 | `phase-19-launch.md` | Hosting, compliance, security, go live | Hosted server |
| S1–S4 | `saas-and-later.md` | Turning it into multi-tenant SaaS | Only on request |

A phase starts only after every acceptance criterion of the previous phase has passed.

Phases 7–18 add their own DocTypes; each phase file lists them.

## Projul feature coverage

| Projul feature | Phase |
|---|---|
| CRM, lead capture, pipeline | 5, 7 |
| Estimating with templates, assemblies and live prices | 7 (dated price library instead of 1build, which is US-only) |
| E-signature, contracts | 8 |
| Selections | 9 |
| Change orders (including from the field) | 10 |
| Scheduling: Gantt, calendar, crew conflicts, schedule sliding | 11 |
| Daily logs, geofenced time tracking, timesheets | 12 |
| Purchase orders, subcontractors | 13 |
| Documents, photos, photo markup, takeoff | 3, 14 |
| Client portal: schedule, selections, documents, change orders, payments, messages | 4, 8–11, 14, 15 |
| Invoicing, progress billing, payment reminders | 6, 15 |
| Payment processing | 15 (Egyptian gateway, sandbox until launch) |
| Accounting sync (QuickBooks in Projul) | Native ERPNext accounting |
| Job costing, WIP, budget variance, time reports | 6, 17 |
| Mobile app, offline, notifications | 3, 16 (PWA) |
| AI connect | 18 |
| Not in Projul: Arabic RTL, EGP, public design catalog, public project pages | 0–5 |
