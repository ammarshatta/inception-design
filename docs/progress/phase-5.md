# Phase 5 — Public pages

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

## What was done

| Task | Where |
|---|---|
| Allowlist API: `list_designs` (filters, sort, 12 per page), `get_public_design`, `get_public_project` (by slug or by share token), `list_public_projects`, `request_design`, `sitemap`. Every function returns named fields only, and every "not available" case raises the same `NotFound`. | `api/public.py` |
| Public image copies: a published design gets public copies of its cover and media (`cover_public`, `Design Media.public_file`). Unpublishing or deleting the design removes them. Project photos use the copy made by "مناسبة للنشر" (phase 3). Public pages only ever use the public copies. | `design_template.py`, `media.py` |
| Server-rendered RTL pages with meta and Open Graph tags: `/`, `/designs`, `/designs/<slug>`, `/projects`, `/projects/<slug>`, `/p/<project>?t=` (`noindex`), `/privacy`, `/data-deletion` | `www/`, `templates/cc_*.html` |
| Sitemap with published designs and public projects only. `robots.txt` blocks `/p/`, `/portal` and `/app`. | `api/public.sitemap`, `setup/install.py` |
| "اطلب تنفيذ" form: creates a Lead (name, mobile, governorate, city, area, design, notes as a comment). It has a honeypot field, a limit of 5 requests per IP per hour, and a consent checkbox. Admins are notified. | `api/public.request_design`, `design_detail.html` |
| Visitors land on the site home; clients and engineers land on `/portal` | `hooks.py` (`home_page`, `role_home_page`) |
| Demo design: cover, 3 renders, a floor plan and a 6-stage template, all drawn in code (no stock photos). Install it with `bench execute construction_core.setup.demo.install`; remove it with `bench execute construction_core.setup.demo.remove`. | `setup/demo.py` |

## Decisions

1. **`public_show_photos = all`** still shows only photos marked "مناسبة للنشر". Showing every photo would need a public copy of every photo, which goes against "the original is never exposed". Change this if you want "all" to copy every non-internal photo automatically.
2. **The client name** is shown only when `public_show_client_name` is on. It is returned as `client_name`, never as a customer record.
3. **The privacy text** is a first draft in Egyptian Arabic, based on the plan. A lawyer must review it before launch (phase 19).

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Playwright: `/` → `/designs` → filter → design (floor plan and stages) → request → the Lead exists | `e2e/public.spec.ts` | ✅ CI |
| Leak test: every public method, with every public setting on, contains none of: phone, mobile, email, amount, customer, internal_only, /private/ | `test_public_site.test_leak_test_every_public_method` | ✅ CI |
| A private project, an unpublished design and an expired or revoked token give an identical 404 | `test_identical_404s`, `test_unpublished_design_404_and_public_copies_removed`, e2e 404 test | ✅ CI |
| The 6th request from one IP within an hour is rejected | `e2e/public.spec.ts` (rate limit) | ✅ CI |
| P05-05: privacy and data-deletion pages in Arabic | e2e | ✅ CI |
| P05-06: the demo removal command deletes the design and its files | `test_demo_remove` | ✅ CI |
