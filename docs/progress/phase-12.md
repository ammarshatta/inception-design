# Phase 12 — Daily logs, timesheets, GPS clock-in

**Status:** 🟢 Unit tests green in CI (run 43971272948, 126 tests). The e2e daily-log test runs with the phase 13 commit.

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate.

## What was done

| Task | Where |
|---|---|
| DocTypes: Daily Log (+ Manpower, + Material rows, photos reuse Stage Update Media) and Clock Event | `doctype/daily_log*`, `doctype/clock_event` |
| One log per project per day. Opening a day with no log pre-fills weather and manpower from the last log | `sitelog.get_daily_log`, `save_daily_log`, `daily_log.py` |
| Clock in/out for one worker or a crew. Location is read only at the moment of the tap, only after the user accepted the Arabic consent text whose version is stored on the event | `sitelog.clock`, `consent`, `accept_consent`, Settings `clock_consent_version` / `clock_consent_text`, User `clock_consent_version` |
| Geofence: haversine distance to `Project.site_latitude/longitude`, radius `site_radius_m` (default 150 m). Outside the radius, or with location off → saved and flagged `needs_approval`; the engineer approves | `sitelog.haversine_m`, `inside_geofence`, `approve_clock_event` |
| Feature flag: `enable_gps_clock_in` in Settings; clocking is refused when it is off | `sitelog.clock` |
| Nightly job: pairs In/Out per employee and project, builds **draft** Timesheets (activity "عمالة موقع", costing rate = crew daily rate ÷ `labor_hours_per_day`). An In without an Out is flagged `unpaired` and not counted. Submitting the Timesheet raises the project's labor cost (ERPNext's own `total_costing_amount`) | `sitelog.build_timesheets`, `pair_events`, `hourly_rate`; scheduler daily in `hooks.py` |
| Permissions: Daily Log and Clock Event are project-scoped for engineers and foremen; clients have no DocPerm on them | `permissions.py`, `hooks.py` |
| Client view: non-internal logs only, work done / issues / photos, no manpower or costs | `sitelog.client_daily_logs` |
| Weekly numbers (days logged, progress) | `sitelog.week_summary` |
| Portal page `/portal/projects/<project>/daily`: clock in/out card, consent sheet, weather chips, manpower rows, work done, issues, internal flag | `frontend/src/pages/DailyLogPage.vue`, link on the project page |
| Fix from phase 11 CI: 1 May 2026 is a Friday and a fixed holiday, which made a duplicate row | `scheduling.ensure_holiday_list` |

## Not done

- **P12-05 weekly summary PDF (Could):** the numbers exist (`week_summary`), the PDF and its weekly email are not built. Left for after the Must stories of later phases.
- Client portal page for daily logs: the API exists (`client_daily_logs`); the page is not added yet.
- Offline clock-in (phase 16 adds the offline queue).

## Decisions to review

1. Clocking without a location (GPS refused or no signal) is still recorded but flagged for approval, so a worker is not lost for a bad signal.
2. Timesheets are left as drafts; the engineer submits them. Only submitted timesheets count in the project's cost.
3. A worker with no Employee link is recorded on the clock event but gets no timesheet (ERPNext timesheets need an Employee).

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| P12-01: today's log exists → same log is edited; new day prefilled from the previous one | `test_sitelog.test_daily_log_one_per_day_and_client_view`; `e2e/daily.spec.ts` reload check | ✅ unit · e2e pending |
| P12-02 AC1: consent accepted, within 150 m → inside the site area | `test_clock_requires_consent_and_stores_version`; `e2e/daily.spec.ts` | ✅ unit · e2e pending |
| P12-02 AC2: far away → saved and flagged for approval | same unit test (≈1.1 km) | ✅ CI |
| P12-02 AC3: no consent → consent shown first, nothing recorded | unit test (PermissionError); e2e shows the sheet before any event exists | ✅ unit · e2e pending |
| P12-03 AC1: matched events → Timesheet; submit raises labor cost by hours × rate | `test_timesheet_from_events_raises_labor_cost` (6 h × 50 = 300) | ✅ CI |
| P12-03 AC2: In without Out → flagged, not counted | same test + `test_pairing_with_missing_out` | ✅ CI |
| P12-04: client sees work done, no manpower | `test_daily_log_one_per_day_and_client_view` | ✅ CI |
| P12-05: weekly PDF | — | ✗ not built (Could) |
| Real phone at the site | Owner check | ☐ (owner) |
