# Screens (draft for engineer review)

**Status:** draft v1, 16 Nov 2026. Engineers have not reviewed it yet, so screens and flows will change. If this file and a phase file disagree, the phase file wins. Note the difference in `docs/progress/phase-N.md`.

## How to use this folder

| Path | What it is |
|---|---|
| `screens/*.png` | The picture of each screen at 390×844 (2x). This is the visual target. |
| `source/*.dc.html` | The mock-up source: layout, Arabic copy, sample data. Use it as a reference only. |
| `FLOWS.md` | The 7 user flows that connect these screens. |

**Rules for building from these mock-ups:**
- Build with frappe-ui components and Tailwind classes in `construction_core/frontend`.
- Do not copy the inline styles or the `DCLogic` script from `source/*.dc.html`. Use them to read the layout, the copy and the states.
- All sample data in the mock-ups is fake. Real screens read from the API. Never ship mock values (CLAUDE.md rule 2).
- Every Arabic string goes through `__()`.
- Prices shown as `[السعر]` are placeholders.

## Design tokens

| Token | Value |
|---|---|
| Font | IBM Plex Sans Arabic 400/500/600/700, served locally with the app; fallback Tahoma |
| Direction | RTL, `lang="ar"`, Western digits, `tabular-nums` for money and percentages |
| Page background | `#F4F5F2` (portal), `#FFFFFF` (public site) |
| Card | white, radius 14–16px, no shadow |
| Text / muted | `#17201D` / `#5B6661` |
| Accent (buttons, active tab, progress) | `#1D6B57`, hover `#14503F` |
| Border | `#E2E5E0`, input `#C9CFC9` |
| Status: paid / done | bg `#E3F0EB`, text `#14503F` |
| Status: due / waiting | bg `#FBEFDF`, text `#8A4A0C` |
| Status: invoiced / approved | bg `#E4ECF8`, text `#1F4687` |
| Status: upcoming | bg `#EEF0EC`, text `#4A5550` |
| Danger | `#B42318` on `#FDE8E6` |
| Touch targets | at least 44px; primary bottom button 52px |
| Client navigation | bottom bar with 5 tabs: الرئيسية · المراحل · الصور · الدفعات · الشات |

## Client portal (`/portal`, role Client, phase 4 unless noted)

| Screen | PNG | Proposed route | Shows | Actions | Phases |
|---|---|---|---|---|---|
| Home | `Main.png` | `/portal` | progress %, planned handover date, current stage, an action card for anything the client must do, latest 3 updates with thumbnails, the next payment | open the selection, the gallery, or payments | 4 |
| Timeline | `ClientTimeline.png` | `/portal/timeline` | stages with planned bar against actual bar, status, dates | open the photos of a stage | 4, 11 |
| Photos | `ClientGallery.png` | `/portal/photos` | photos and videos grouped by update, filter chips by stage | filter by stage; open a photo or video full screen | 3, 4 |
| Finish selection | `ClientSelections.png` | `/portal/selections/:name` | options with price per m², the allowance, a live difference for the quantity | pick an option; if it is over the allowance, the client is sent to sign a change order | 9, 10 |
| Sign change order | `ClientSign.png` | `/portal/change-orders/:name/sign` | scope, price, schedule impact, a drawn-signature box, an OTP code | sign or reject | 8, 10 |
| Payments | `ClientPayments.png` | `/portal/payments` | contract total, paid, remaining; milestone rows with a status pill | pay online; upload a transfer receipt; download the invoice PDF | 6, 15 |
| Project chat | `ClientChat.png` | `/portal/chat` | one thread per project with the engineer and the office; photo messages; link cards (change order, invoice) | send text or a photo; quick replies | 4 |

## Engineer and foreman portal (`/portal`, roles Site Engineer and Foreman)

| Screen | PNG | Proposed route | Shows | Actions | Phases |
|---|---|---|---|---|---|
| My projects | `EngineerProjects.png` | `/portal/eng` | today's work card, a sync-queue badge, projects with progress and flags (late selection, no update for 3 days), shortcuts to stages, workers and materials | new update; clock the crew in | 3, 16 |
| New update | `EngineerUpdate.png` | `/portal/eng/update/new` | stage, note, photo grid with per-file upload progress or failure, stage progress slider, "internal only" toggle, a "for publishing" badge per photo | upload photos/video (1 min / 50 MB); retry a failed upload; publish | 3, 16 |
| Clock-in and daily log | `ForemanClockIn.png` | `/portal/eng/clock-in` | geofence status and accuracy, crew checklist, weather chips, materials used, issues | clock in N workers (location is saved only at clock-in and clock-out) | 12 |
| Project stages | `EngineerStages.png` | `/portal/eng/projects/:id/stages` | stages from a template with weight, dates and status, total weight = 100%, drag to reorder | add a stage from the library or a custom one (weight, duration, after which stage, crew, visible to client) | 1, 11 |
| Workers | `EngineerWorkers.png` | `/portal/eng/crews/:id/workers` | crew tabs; workers with trade, daily wage, days worked | add a worker (name, mobile, trade, wage, crew); national ID is not collected | 11, 12 |
| Materials | `EngineerMaterials.png` | `/portal/eng/projects/:id/materials` | counts (waiting approval, on the way, delivered this month); lines with quantity, stage, used and left | request a material (goes to the office for approval and supplier choice); record delivery with an invoice photo | 13 |

**Open permission question:** who adds stages and workers, the office or the engineer? Until the engineers answer, build these screens behind the permission checks in phase 1 so the role can be switched without code changes.

## Public website (Jinja in `construction_core/www`, phase 5)

| Screen | PNG | Proposed route | Shows | Actions |
|---|---|---|---|---|
| Design catalog | `PublicCatalog.png` | `/designs` | office name, filters (area, rooms, style, price), design cards with cover, specs, duration and a cost range | filter; open a design; request execution |
| Design and request | `PublicDesign.png` | `/designs/<slug>` | gallery and floor plan, cost range, specs, execution stages, request form (name, Egyptian mobile, governorate, area, consent checkbox) | submit, which creates a Lead (phase 7) |

## Open questions for engineers (also on the design board)

- Client: is the home screen showing what clients ask about most? Should payments show amounts before invoicing? Is the allowance per m² or per room? Is a code plus a drawn signature enough for change orders? One chat thread per project, or separate threads? Should messages after 6 PM wait until morning?
- Engineers: one update per stage per day, or more? Is progress % typed in, or does it come only from the checklist? Clock-in per crew by the foreman, or per worker? What else must the daily log capture? Who adds stages and workers? Does every material request need approval, or only those above an amount?
- Sales: which filters do buyers use first? Show a cost range or a "from" price? What must the request form ask before a site visit?
