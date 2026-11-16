# Phase 17 — Reports and dashboards

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate.

## What was built

All numbers come from one module, `construction_core/analytics.py`, so the reports, the number cards, the portal and the weekly PDF always agree. Every function first narrows to the projects the user may see (`allowed_projects`, through Frappe's permission query), and every query is grouped (no query per project).

| Report (desk → "لوحة المدير") | Content | Filters |
|---|---|---|
| **CC WIP** (أعمال تحت التنفيذ) | contract (milestones incl. change orders), % complete, earned value, billed, over/under billing, cost to date (purchases + timesheets), cost at completion, projected margin; chart earned vs billed | company, project, engineer, dates |
| **CC Job Costing** | budget (approved estimate cost by section = stage) vs committed (open POs, unclaimed subcontracts) vs actual (purchase invoices by item group, subcontract claims, timesheets) by stage and type | same |
| **CC Budget Variance** | job-costing lines over budget by more than X% (default 10), with the project's approved change orders as reasons | same + threshold |
| **CC Labor** | hours, cost, overtime (above the daily hours in Settings) and out-of-area clock events by project, crew and employee | same |
| **CC Sales Pipeline** | opportunities by stage (count, value), won/lost, conversion, average estimate, loss reasons, lead source; chart | company, dates |
| **CC Collections** | outstanding per customer and project in 0-30 / 31-60 / 61-90 / 90+ buckets, overdue, and milestones due in the next 30 and 60 days | same |
| **CC Selections Status** | open, overdue, awaiting signature, approved per project | same |
| **CC Schedule Status** | projects behind schedule by days, with the worst stage | same |

Excel export and printing come with Frappe's report view.

| Task | Where |
|---|---|
| **لوحة المدير** workspace: number cards active projects, WIP over/under billing, receivables, overdue, late projects, pipeline value. Each card is a Report card, so it opens its report (drill-down to the rows, and from each row to the document) | `workspace/لوحة المدير`, `number_card/cc_*` |
| Engineer dashboard on the portal home: today's tasks, overdue selections, approvals waiting for the client and new client change requests, only from the engineer's projects | `analytics.engineer_dashboard`, `Home.vue` |
| Weekly summary PDF to the office admins every Saturday at 9 AM (when an email account is set), print format "Inceptiondesign Weekly Summary" | `analytics.send_weekly_summary` (cron in `hooks.py`) |

## Not done

- Report names in the desk are English internal names (CC …); the workspace shortcuts show the Arabic names. Renaming the reports to Arabic is a one-line change each if the owner prefers.
- The weekly client summary from phase 12 (P12-05) can reuse the same print approach; not built yet.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| WIP math on a seeded project with known numbers | `test_analytics.TestWip` (pure + seeded: contract 100,000, 40%, billed 30,000 → earned 40,000, under-billed 10,000, EAC 30,000) | ✅ CI |
| Report totals tie to ERPNext's own reports | job costing actual = GL expense for the project; collections = ERPNext Accounts Receivable for the invoice | ✅ CI |
| 200 seeded projects, every report under 3 s | `test_two_hundred_projects_under_three_seconds` — CI timings with 202 projects: WIP 0.010 s, job costing 0.006, variance 0.008, labor 0.002, collections 0.002, selections 0.002, schedule 0.003, pipeline 0.001, dashboard 0.015 | ✅ CI |
| An engineer sees only their projects in every report | `test_engineer_sees_only_own_projects_in_every_report` | ✅ CI |
| Saturday 9 AM summary PDF | needs an email account on a real site | ☐ (owner) |
