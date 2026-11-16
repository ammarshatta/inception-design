# Progress tracker

Updated: **16 Nov 2026**. Update this file at the end of every session.

**Status values**
- ⬜ Not started
- 🟡 Code written, **not run yet**
- 🔵 In progress
- ✅ Done: tests pass, and every acceptance criterion has evidence
- ✅ (CI) means verified in GitHub Actions on a fresh site; one local install is still recommended
- ⛔ Blocked

**Where work happens**
- **Cloud:** a Claude cloud session. There is no ERPNext there, so code can be written but not run.
- **Local:** Claude Code on the owner's computer, inside the frappe_docker devcontainer.

## Phases

| # | Phase | Status | Where | Report | Notes |
|---|---|---|---|---|---|
| 0 | Foundation: app, portal skeleton, CI | ✅ (CI) | Cloud + CI | [phase-0.md](phase-0.md) | CI green: install, 33 tests, portal build, 2 Playwright tests. One local install is still to do. |
| 1 | Data model and permissions | ✅ (CI) | Cloud + CI | [phase-1.md](phase-1.md) | Every required test passes in CI. Review the 4 decisions. |
| 2 | Admin screens, client onboarding | 🔵 | Cloud + CI | [phase-2.md](phase-2.md) | Code written, waiting for CI |
| 3 | Engineer portal, photo uploads | 🔵 | Cloud + CI | [phase-3.md](phase-3.md) | Code written, waiting for CI |
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

## Working mode (decided 16 Nov 2026)

The owner asked for all phases to be built in a row and reviewed once at the end.
- No approval is needed between phases.
- CI must be green before the next phase starts.
- Work stops only for paid services, accounts in the owner's name, phase 19 hosting, and legal questions.
- Anything that needs a real phone, a real account or a manual check goes into "Owner checks at the end" below.

## Owner checks at the end

| Check | Phase |
|---|---|
| Timed admin run (under 3 minutes): project from a template + 2 clients + share link | 2 |
| Install the portal on an Android phone from Chrome (Add to home screen) | 3 |

## Next actions (owner)

1. [ ] Follow `docs/LOCAL-SETUP.md`, steps 1–6, to install the app on your bench.
2. [ ] Open `/portal` on your site and run the tests once locally.
3. [x] CI on GitHub is green: [run 43934298054](https://github.com/ammarshatta/inception-design/actions/runs/43934298054).
4. [ ] Share the design board and the flows board with the engineers and collect feedback (open questions are in `docs/design/SCREENS.md`).
5. [ ] Approve phase 2 only after phases 0 and 1 are ✅.

## Open decisions

| Decision | Waiting for | Affects |
|---|---|---|
| Who adds stages and workers: the office or the engineer? | Engineers' feedback | Phases 2, 3, 11 |
| Is one chat thread per project enough? | Engineers' feedback | Phase 4 |
| Construction Engineer is set with desk access **off**, as `phase-01` says. The roles table in `00-overview.md` calls it a "System User". | Owner | Phase 1 roles |
| Does every material request need approval, or only those above an amount? | Engineers' feedback | Phase 13 |
| Adding a client to a project sends ERPNext's welcome email, so a site needs an email account | Phase 2 design | Phase 2 |

## Session log

| Date | Where | What |
|---|---|---|
| 16 Nov 2026 | Cloud | Phases 0 and 1 code written. Plan, backlog and design docs added. |
| 16 Nov 2026 | CI | 8 CI runs. Fixed welcome emails, the permission test method, the portal build path and the office-name fallback. All green. |
