# Phase 11 — Scheduling and crews

**Status:** 🔵 Code written on 17 Nov 2026; waiting for CI.

## What was done

| Task | Where |
|---|---|
| DocTypes: Crew (+ Crew Member: trade, phone, daily rate) and Crew Assignment (crew or subcontractor, project, task, dates, status) | `doctype/crew*`, `crew_assignment` |
| Gantt: ERPNext's own Task Gantt (`/app/task/view/gantt?project=…`), which already supports dragging and finish-to-start dependencies. Tasks now have a `project_stage` field (the kickoff fills it), and moving tasks rolls the stage's planned dates up (min start / max end). | custom field `Task.project_stage`, `scheduling.task_on_update` |
| Company calendar of assignments (`/app/crew-assignment/view/calendar`), filterable by crew, subcontractor, project and status | `crew_assignment_calendar.js` |
| Conflict detection: an overlapping assignment for the same crew or subcontractor gives a warning that names the other project. It does not block the save, and the override is logged as a comment. | `crew_assignment.py`, `scheduling.overlapping` |
| "أجّل" on a task: moves the task and every task that depends on it (the whole chain) by N working days. It skips Fridays and the holidays in "إجازات المقاولات", shows a preview, and notifies the crews' foremen and the client. | `scheduling.slide_task`, `public/js/task.js` |
| Holiday list "إجازات المقاولات": Fridays plus the fixed Egyptian holidays. The office adds the Islamic holidays each year, because their dates move. | `scheduling.ensure_holiday_list` |
| Client timeline with planned vs actual dates and delays | Done in phase 4 |
| Foreman portal view (`/portal/foreman`): "شغلي النهارده" and "الأسبوع ده", showing only the crews they lead, with the project address and a map link. New role **Construction Foreman** (portal). | `scheduling.foreman_assignments`, `ForemanPage.vue`, `Project.site_*` fields |

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Working-day slide across a Friday, across a holiday, and along a chain of 3 dependencies | `test_scheduling.TestWorkingDays` | pending CI |
| An overlap warning names the other project | `test_overlap_warns_and_names_project` | pending CI |
| Stage dates update when tasks move | `test_stage_dates_follow_tasks` | pending CI |
| Playwright: drag a task in the Gantt | ⚠️ Not automated. The drag is ERPNext's own Gantt (it calls `frappe.desk.gantt.update_task`); our roll-up on save is tested. Check it by hand. | ☐ (owner) |
| The foreman's view shows only their crew's assignments | `test_foreman_sees_only_own_crew` | pending CI |
