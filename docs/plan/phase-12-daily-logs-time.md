# Phase 12 — Daily logs, timesheets and GPS clock-in

## Goal
Every site day is recorded: who was there, what was done, what was used, and any problems. Labor hours feed job costing automatically.

Projul equivalents: daily logs, geofenced GPS time tracking, and timesheets.

## Privacy note (for the owner)

Location tracking of workers is personal data under Egypt's Personal Data Protection Law (151/2020). Its executive regulations took effect on 1 Nov 2025, with enforcement expected from about 1 Nov 2026. So:
- Location is captured **only at clock-in and clock-out**, never continuously, and only after the worker or foreman accepts an in-app Arabic consent notice.
- Ask a lawyer about your obligations (licensing and a DPO) before launch. Phase 19 has a compliance checklist.

## Reuse from ERPNext
- **`Timesheet`** and `Activity Type` for hours and costing rates.
- **`Employee`** and the `Project` costing fields.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Site Location` | child of Project, or fields on Project | latitude, longitude, radius_m (default 150), address |
| `Daily Log` | normal | project, log_date, author, weather (Select: صافي, حر شديد, مطر, رياح/تراب), manpower (table: `Daily Log Manpower`), work_done, materials_used (table: `Daily Log Material`), equipment, issues, visitors, photos (table, same as Stage Update Media), internal_only |
| `Daily Log Manpower` | child | crew or supplier, trade, headcount, hours |
| `Daily Log Material` | child | item, qty, uom, project_stage |
| `Clock Event` | normal | employee or crew, project, event (In / Out), at, latitude, longitude, accuracy_m, distance_m, inside_geofence, device_info, consent_version |

## Tasks

1. **Daily log in the portal (engineer or foreman):**
   - One log per project per day; editing reopens the same one.
   - Quick entry with the defaults of the previous day.
   - Photos use the phase 3 pipeline.
   - Material use can create an ERPNext `Stock Entry` (Material Issue) to the project when stock is tracked (setting, off by default).
2. **Clock-in and clock-out (portal, foreman for the crew or a worker with a phone):**
   - Uses the browser Geolocation API.
   - Distance to the site is computed with the haversine formula.
   - **Outside the radius:** still recorded, but flagged and needing engineer approval.
   - **Location turned off:** the event is recorded with no location and flagged.
3. **Timesheets:**
   - A nightly job builds draft ERPNext `Timesheet` records from paired clock events, per employee per project.
   - The engineer reviews and submits them. The costing rate comes from `Activity Type` or the crew member's daily rate.
   - Submitted timesheets update the project's labor cost (ERPNext project costing).
4. **Subcontractor manpower** is recorded in the daily log only, not as timesheets. Its cost comes from the subcontract in phase 13.
5. **Client view:** the client sees the daily logs that are not `internal_only` (work done and photos), without the manpower costs.
6. **Weekly summary PDF** per project, for the client: days worked, progress, photos.

## Acceptance criteria
- [ ] Haversine unit tests: inside, at the edge and outside the radius.
- [ ] Clock-in without consent is impossible; the consent version is stored (test).
- [ ] Paired In/Out events produce the right hours, including a missing Out (flagged, not counted) (test).
- [ ] A submitted timesheet raises the project's labor cost by hours × rate (test against the ERPNext fields).
- [ ] Clients never see manpower, costs or `internal_only` logs (permission test).
