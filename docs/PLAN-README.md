# Inceptiondesign plan v3 (November 2026)

A full plan for Claude Code, covering every Projul feature, built SaaS-ready:
- **Phases 0–18:** the whole platform is built and tested on your computer, at no cost.
- **Phase 19 (launch):** hosting, data-protection compliance, security checks, and go live.
- **S1–S4:** turning it into a multi-tenant SaaS, only when you decide.

## Files

| File | For | Purpose |
|---|---|---|
| `LOCAL-SETUP.md` | You | Install and run ERPNext locally, then start Claude Code |
| `CLAUDE.md` | Claude Code | Project rules; it reads this automatically every session |
| `docs/plan/00-overview.md` | Both | Decision, architecture, roles, core data model, phase list, Projul coverage table |
| `docs/plan/phase-00-…` to `phase-19-launch.md` | Claude Code | One phase per file, with DocTypes, tasks and acceptance criteria |
| `docs/plan/hosting-options.md` | You | VPS vs Frappe Cloud, costs, and the Egypt data-location question |
| `docs/plan/saas-and-later.md` | Both | SaaS-readiness rules, licensing, SaaS phases, later features |
| `docs/backlog/` | Both | 125 user stories with Given/When/Then criteria, one file per phase, plus `stories.csv` for Excel |
| `docs/design/SCREENS.md` + `screens/*.png` | Claude Code | 15 draft screens, routes, design tokens; mock-up sources in `source/` |
| `docs/design/FLOWS.md` | Both | The 7 user flows with open questions for engineers |

## How to start

1. Follow `LOCAL-SETUP.md`, Level 1, to see ERPNext. It takes about 10 minutes.
2. Follow Level 2 to build the real dev environment.
3. Copy `CLAUDE.md` and `docs/` into the bench folder, then start Claude Code with the message in `LOCAL-SETUP.md`, step 6.
4. Run one phase per Claude Code session. Read `docs/progress/phase-N.md` before approving the next phase.
5. Before phase 19, choose hosting, get the accounts listed in `docs/plan/phase-19-launch.md`, and go through its data-protection checklist with a lawyer.

## What you need to decide or approve along the way

| When | Decision |
|---|---|
| Phase 8 | Ask a lawyer whether the built-in e-signature (drawn signature + code + audit trail) is enough, or whether you need a licensed provider for big contracts |
| Phase 12 | The Arabic consent text for GPS clock-in |
| Phase 15 | A payment gateway (Paymob or another). Its sandbox is free; live fees are per transaction |
| Phase 18 | The AI provider and the monthly cap |
| Phase 19 | Hosting location (Egypt PDPL), licence, DPO, and server size (8 or 12 GB) |

## What changed from v2

- **Twelve new phases (7–18)** cover the Projul features that were missing:
  - pipeline and estimating
  - e-signature
  - selections
  - change orders
  - scheduling and crews
  - daily logs and GPS time
  - subcontractors and purchasing
  - documents, markup and takeoff
  - online payments and reminders
  - offline mobile and push notifications
  - reports
  - the AI assistant and MCP connector
- **SaaS-ready rules from day one:**
  - no hardcoded office details
  - multi-site safe code
  - no AGPL dependencies
  - feature flags per site
- **Launch moved to phase 19.** It now includes the Egypt data-protection checklist and the switch-on of live integrations.
