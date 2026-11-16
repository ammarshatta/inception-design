# Phase 5 — Public pages

## Goal
A visitor without an account can browse designs, open one, and request it; the request lands in ERPNext as a Lead. Published projects are visible with no private data leaking.

## Tasks

1. **Allowlist API** in `api/public.py` (`allow_guest=True`):
   - **`list_designs(filters, sort, page)`** and **`get_public_design(slug)`:** return named fields only, for `published = 1` designs.
   - **`get_public_project(slug=None, token=None)`:**
     - checks visibility and expiry
     - checks the token by comparing SHA-256 hashes with `hmac.compare_digest`
     - returns only the fields its `public_show_*` settings allow
   - Private, missing, expired and revoked items all return the same 404.
2. **Public copies of images:**
   - When a photo is marked publishable (or added to a published design), create a **separate public copy** and store it in `public_file`. Public pages only ever use `public_file`.
   - When the mark is removed, delete the copy.
   - The original private file is never exposed.
3. **Pages** in `www/` (Jinja, server-rendered, RTL):
   - **`/`** — home: featured designs, published projects, and a "اطلب تنفيذ" call to action.
   - **`/designs`:**
     - filters: area, bedrooms, bathrooms, style, price range
     - sort, and 12 designs per page
   - **`/designs/<slug>`:** gallery, floor plans, stages from the phase template, duration, "التكلفة التقديرية من … لـ …", and the request form.
   - **`/projects`, `/projects/<slug>`, `/p/<token>`.** Add `noindex` on `/p/`.
   - **`/privacy`** and **`/data-deletion`** (needed for Facebook login in phase 19).
   - **SEO:** meta tags, Open Graph, and a sitemap of published designs and public projects only.
4. **"اطلب تنفيذ" form:**
   - Creates a `Lead` with: name, Egyptian mobile, governorate, city, apartment area, `design_template`, notes.
   - Anti-spam:
     - a rate limit of 5 requests per hour per IP (`frappe.rate_limiter.rate_limit`)
     - a hidden honeypot field
   - Email the admin.
5. **Demo content:**
   - One complete sample design: cover, 3 renders, 1 floor plan, 6 stages.
   - A `bench execute construction_core.setup.demo.remove` command deletes it before launch.

## Acceptance criteria
- [ ] Playwright: a visitor opens `/`, then `/designs`, applies a filter, opens a design, sees the floor plan and stages, and submits a request. The Lead appears in `/app/lead`.
- [ ] A leak test calls every `api/public.py` method for a project with every public setting on. It fails if any key or value contains any of:
  - `phone`, `mobile`, `email`
  - `amount`, `customer`, `internal_only`
  - `/private/`
- [ ] A private project, an unpublished design, and an expired or revoked token each return an identical 404.
- [ ] The 6th request from one IP within an hour is rejected.
