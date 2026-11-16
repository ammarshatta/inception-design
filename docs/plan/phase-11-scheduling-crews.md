# Phase 11 — Scheduling and crews

## Goal
The office plans every project on a Gantt and a calendar, assigns crews and subcontractors, sees conflicts before they happen, and slides the schedule when there is a delay. The client sees a simple timeline.

Projul equivalents: scheduling with Gantt and calendar views, crew and sub conflict detection, and schedule sliding.

## Reuse from ERPNext
- **`Task`** with `exp_start_date`, `exp_end_date` and `depends_on`. ERPNext already has a Gantt view for Tasks; extend it rather than replace it.
- **`Employee`** for staff and foremen.
- **`Supplier`** for subcontractors.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Crew` | normal | crew_name (e.g. فريق محارة 1), foreman (Employee), members (table: `Crew Member`), trade, active |
| `Crew Member` | child | employee or worker_name, phone, daily_rate |
| `Crew Assignment` | normal | crew or supplier, project, task, from_date, to_date, notes, status |
| `Holiday List` (ERPNext) | reuse | Fridays and Egyptian public holidays |

## Tasks

1. **Project Gantt:**
   - Use frappe-gantt (MIT, by Frappe) in the desk.
   - Drag to change dates, and draw dependencies (finish-to-start).
   - Rolling a `Task` up to its `Project Stage` sets the stage's planned dates.
2. **Company calendar:** one calendar of all assignments, filterable by crew, subcontractor, project and engineer. Day, week and month views.
3. **Conflict detection:**
   - Saving a `Crew Assignment` warns when the same crew or subcontractor overlaps another assignment.
   - The warning lists the conflicting project.
   - It does not block, so the admin can override, but the override is logged.
4. **Schedule slide:**
   - A "أجّل" action on a task moves it and every dependent task by N working days (skipping the Holiday List).
   - Show a preview before applying.
   - Notify the affected crews' foremen and the client.
5. **Client timeline:** the portal shows stages with planned and actual bars (read only), and highlights delays.
6. **Foreman view (portal):**
   - "شغلي النهارده" and "الأسبوع ده": the foreman's crew assignments, with the project address and a map link.

## Acceptance criteria
- [ ] Unit tests for the working-day slide: across a Friday, across a holiday, and with a dependency chain of 3.
- [ ] An overlap test produces a warning that names the other project.
- [ ] Stage dates update when tasks move (test).
- [ ] Playwright: drag a task in the Gantt and confirm the saved dates.
- [ ] The foreman's view shows only that crew's assignments (permission test).
