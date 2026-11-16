# Phase 17 — Reports and dashboards

## Goal
The owner sees the health of the business on one page, and every number can be drilled down to its source documents.

Projul equivalents: job costing, WIP, time tracking summaries, budget variance and sales reports.

## Reports (Script Reports in `construction_core`, all with filters for date, project, engineer and company)

| Report | Content |
|---|---|
| **WIP (أعمال تحت التنفيذ)** | Per active project: contract value incl. approved change orders, % complete (weighted), earned value = contract × % complete, billed to date, over or under billing, cost to date, estimated cost at completion, projected margin |
| **Job costing** | Budget versus committed (POs and subcontracts) versus actual, by stage and by type (material, labor, subcontract, equipment, other) |
| **Budget variance** | Lines over budget by more than X%, with the reason fields from change orders |
| **Labor** | Hours and cost by project, crew and employee; overtime; flagged out-of-geofence clock-ins |
| **Sales pipeline** | Opportunities by stage, conversion rate, average estimate value, win/loss reasons, lead source |
| **Collections** | ERPNext Accounts Receivable aging, plus upcoming milestones for the next 30 and 60 days |
| **Selections status** | Open and overdue selections per project |
| **Schedule** | Projects behind schedule and by how many days |

## Tasks

1. Build the reports above with **charts** (Frappe charts) and **Excel export** (built in).
2. **"لوحة المدير" workspace** with number cards:
   - active projects
   - total WIP over or under billing
   - receivables
   - overdue
   - projects late
   - the pipeline value
3. **Engineer dashboard in the portal:** their projects, today's tasks, overdue selections, and pending approvals.
4. **Scheduled email:** a weekly summary PDF to the owner every Saturday at 9 AM.
5. **Performance:** every report runs in under 3 s with 200 projects of seeded data.

## Acceptance criteria
- [ ] The WIP math is tested on a seeded project with known numbers (earned value, over/under billing).
- [ ] Every report total ties to ERPNext's own reports (General Ledger, AR, project costing) in tests.
- [ ] The performance test with 200 seeded projects meets the 3 s target (timings in the report).
- [ ] Permission test: an engineer sees only their projects in every report.
