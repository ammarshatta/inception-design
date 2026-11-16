# Progress tracker

Updated: **16 Nov 2026**. Update this file at the end of every session.

**Status values**
- ⬜ Not started
- 🟡 Code written, **not run yet**
- 🔵 In progress
- ✅ Done: tests pass on the owner's computer, and every acceptance criterion has evidence
- ⛔ Blocked

**Where work happens**
- **Cloud:** a Claude cloud session. There is no ERPNext there, so code can be written but not run.
- **Local:** Claude Code on the owner's computer, inside the frappe_docker devcontainer.

## Phases

| # | Phase | Status | Where | Report | Notes |
|---|---|---|---|---|---|
| 0 | Foundation: app, portal skeleton, CI | 🟡 | Cloud | [phase-0.md](phase-0.md) | Needs a local install and test run, plus a green CI run |
| 1 | Data model and permissions | 🟡 | Cloud | [phase-1.md](phase-1.md) | 11 DocTypes and 33 tests written; none run yet |
| 2 | Admin screens, client onboarding | ⬜ | | | |
| 3 | Engineer portal, photo uploads | ⬜ | | | Screens: `docs/design/SCREENS.md` |
| 4 | Client portal, chat, approvals | ⬜ | | | Screens drafted |
| 5 | Design catalog, public pages, lead form | ⬜ | | | Screens drafted |
| 6 | Money: milestones, invoices, expenses | ⬜ | | | |
| 7 | Sales and estimating | ⬜ | | | |
| 8 | Proposals and e-signature | ⬜ | | | |
| 9 | Finish selections | ⬜ | | | |
| 10 | Change orders | ⬜ | | | |
| 11 | Scheduling and crews | ⬜ | | | |
| 12 | Daily logs, timesheets, GPS clock-in | ⬜ | | | |
| 13 | Subcontractors and procurement | ⬜ | | | |
| 14 | Documents, markup, takeoff | ⬜ | | | |
| 15 | Online payments and reminders | ⬜ | | | |
| 16 | Offline PWA and push | ⬜ | | | |
| 17 | Reports and dashboards | ⬜ | | | |
| 18 | AI assistant | ⬜ | | | |
| 19 | Launch: hosting and compliance | ⬜ | | | The first time a server is involved |

## Next actions (owner)

1. [ ] Follow `docs/LOCAL-SETUP.md`, steps 1–6, to install the app on your bench.
2. [ ] Run the tests (`bench --site inceptiondesign.localhost run-tests --app construction_core`). Then ask Claude Code to fix what fails and fill in the "Verified on the owner's computer" sections.
3. [ ] Check that the first CI run on GitHub (Actions tab) is green.
4. [ ] Share the design board and the flows board with the engineers and collect feedback (open questions are in `docs/design/SCREENS.md`).
5. [ ] Approve phase 2 only after phases 0 and 1 are ✅.

## Open decisions

| Decision | Waiting for | Affects |
|---|---|---|
| Who adds stages and workers: the office or the engineer? | Engineers' feedback | Phases 2, 3, 11 |
| Is one chat thread per project enough? | Engineers' feedback | Phase 4 |
| Construction Engineer is set with desk access **off**, as `phase-01` says. The roles table in `00-overview.md` calls it a "System User". | Owner | Phase 1 roles |
| Does every material request need approval, or only those above an amount? | Engineers' feedback | Phase 13 |

## Session log

| Date | Where | What |
|---|---|---|
| 16 Nov 2026 | Cloud | Phases 0 and 1 code written. Plan, backlog and design docs added. Not run. |
