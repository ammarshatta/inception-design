# Inceptiondesign — construction and finishing project platform

Inceptiondesign is a platform for an Egyptian contracting and apartment-finishing office:
- project tracking by weighted stages with site photos
- a client portal and a mobile-friendly engineer portal
- a public design catalog that turns visitors into leads
- payments and expenses booked in ERPNext accounting
- the Projul-level toolset:
  - sales pipeline, estimating, e-signed proposals, finish selections, change orders
  - scheduling and crews, daily logs and GPS clock-in
  - subcontractors and procurement, documents, markup and takeoff
  - online payments, offline mobile, reports, and an AI assistant
- built so it can become a multi-tenant SaaS later (see `docs/plan/saas-and-later.md`)

The full plan is in `docs/plan/`. Read `docs/plan/00-overview.md` first, then only the file for the phase you are working on.

For each phase, also read:
- `docs/backlog/phase-NN.md`: the user stories and Given/When/Then acceptance criteria. Report each criterion's result in `docs/progress/phase-N.md`.
- `docs/design/SCREENS.md`: when the phase has UI. Open only the screen PNGs listed for that phase, and follow the design tokens.
- `docs/design/FLOWS.md`: when the phase touches a user flow.

Screens and flows are drafts that will change after engineer review. If they conflict with a phase file, the phase file wins; note the conflict.

## Stack (pinned — do not change without asking)

- Frappe Framework v16 + ERPNext v16 (`version-16` branches; the exact tag is recorded in `docs/versions.md`)
- Python 3.14, Node 24, Yarn 1.22, MariaDB and Redis as shipped by frappe_docker for v16
- Custom Frappe app: `construction_core` (all our code lives here)
- Portal UI: Vue 3 + frappe-ui + Tailwind in `construction_core/frontend`, served at `/portal`
- Public pages: Frappe website pages (Jinja) in `construction_core/www`
- Realtime: Frappe Realtime (built-in Socket.IO)
- Phases 0–18: everything runs locally in the frappe_docker devcontainer on the owner's computer. There is no server.
- Phase 19: a hosted VPS (or Frappe Cloud) with our custom image. After launch, updates go out only with `deploy/deploy.sh <tag>`.

## Working rules

1. **One phase at a time.**
   - Before coding, write your plan in `docs/progress/phase-N.md` and wait for approval.
   - At the end, run the tests and fill in the same file:
     - what changed
     - what is not done
     - each acceptance criterion with pass or fail and its evidence
2. **Never claim something works until it runs and is tested.**
   - No hardcoded data in place of database records.
   - No fake implementations that only look functional.
   - No TODOs in critical paths.
3. **Never edit frappe or erpnext source.** Put every change in `construction_core`: hooks, custom fields, fixtures, patches, or overrides.
4. **Check before you build.** Before building anything, check whether Frappe or ERPNext already has it. Read the v16 docs and the installed source code; do not rely on memory.
5. **Permissions are enforced on the server only.**
   - Every `@frappe.whitelist()` method checks access with `frappe.has_permission` or the helpers in `permissions.py`.
   - Never trust a project ID sent by the browser.
   - `allow_guest=True` is allowed only in `api/public.py`.
6. **Public output is an allowlist.** Never add a field to `get_public_project()` or `get_public_design()` without an explicit request.
7. **Money is never a raw float.**
   - Use Currency fields with `flt(value, precision)`, or `Decimal` in calculations.
   - Submitted invoices and approved quotations never change.
   - Corrections go through cancel and amend.
8. **User-facing text is Egyptian Arabic.**
   - Wrap every string with `_()` in Python and `__()` in JS/Vue.
   - Interfaces are RTL; numbers use Western digits (123).
9. **No secrets in git.**
   - Real values live in `.env` or `site_config.json` outside the repo.
   - Keep `.env.example` up to date with empty values.
10. **No paid services, subscriptions, or heavy new processes without approval.** Write down the cost and ask first.
11. **Do not reuse core DocType names.** Never use `Communication`, `Notification`, `Comment`, `File`, `Project Update`, or `Contract`.
12. **Stop and ask** when:
    - a decision is not covered by the plan
    - a dependency does not work on v16
    - an acceptance criterion cannot be met
13. **Commit at the end of each phase** with the message `phase-N: <summary>`.
14. **No hosting before phase 19.**
    - Do not set up servers, domains or paid accounts before phase 19.
    - After launch, change the live site only through a tagged release and `deploy/deploy.sh`, after CI is green and the owner approves.
    - Never copy live client data to a development machine.
    - Free sandbox or test accounts (for example the payment gateway sandbox, or a Google OAuth test client) are allowed earlier, but only with the owner's own account and approval.
15. **SaaS-ready from day one** (details in `docs/plan/saas-and-later.md`):
    - Never hardcode the office name, logo, colors, phone numbers or terms. They live in the single DocType `Inceptiondesign Settings` and ERPNext `Company`.
    - All code must work when many sites share one bench. Never read or write across sites.
    - No AGPL dependencies (for example Frappe CRM, Helpdesk or Press) without approval.
    - Each major feature (selections, GPS, online payments, AI) has an on/off flag in Settings.
16. **Personal data.**
    - Collect only what a feature needs.
    - Location is captured only at clock-in and clock-out, and only after consent.
    - Keep privacy notices in Arabic.
    - Never log passwords, OTPs, gateway secrets or full card data.
    - Egypt's data protection law (151/2020) applies; phase 19 has the compliance checklist.

## Useful commands (inside the devcontainer, in `frappe-bench`)

```bash
bench start                                              # run the dev server
bench --site inceptiondesign.localhost migrate
bench --site inceptiondesign.localhost run-tests --app construction_core
bench --site inceptiondesign.localhost export-fixtures --app construction_core
bench build --app construction_core
cd apps/construction_core/frontend && yarn dev           # portal dev server (port 8080)
```
