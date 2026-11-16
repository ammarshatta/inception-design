# Phase 0 — Local foundation

## Goal
`construction_core` exists and is installed on `inceptiondesign.localhost`. CI runs its tests, and the repo is on GitHub.

Everything runs on the owner's computer. There is no server, domain or paid service until phase 19.

## Preconditions (done by the owner, see `LOCAL-SETUP.md`)
- The devcontainer is running, with the bench at `/workspace/development/frappe-bench`.
- ERPNext v16 is installed on `inceptiondesign.localhost`, and the setup wizard is done (Arabic, Egypt, EGP, Africa/Cairo).
- `CLAUDE.md` and `docs/` are in the bench folder.
- An empty private GitHub repo named `inceptiondesign` exists.

If any of these is missing, stop and say so.

## Tasks

1. **Dependency report** in `docs/versions.md`:
   - For each of frappe, erpnext, frappe_docker and frappe-ui, record:
     - the installed version or tag (`bench version`)
     - the license
     - the date of the last release
   - Note Quantbit Construction Management and BuildSuite as references only.
2. **Create the app:**
   - Run `bench new-app construction_core` (title "Construction Core", license MIT).
   - Install it on the site.
   - Create the module "Construction Core".
3. **Make the app folder the repo:**
   - Move `CLAUDE.md` and `docs/` from the bench folder into `apps/construction_core/`.
   - Add `.env.example` and a `.gitignore` that excludes `node_modules`, `.env` and built assets.
   - Push to GitHub.
4. **Portal skeleton:**
   - Inside the app, run `npx degit netchampfaris/frappe-ui-starter frontend`. The same starter is published at `github.com/frappe/frappe-ui-starter`; use the current one and note it in `docs/versions.md`.
   - Change the router base to `/portal`.
   - Wire the build output and `www/portal.html` the way the starter and Frappe's own apps (Helpdesk, CRM) do.
   - Set `dir="rtl"` and `lang="ar"`, and load IBM Plex Sans Arabic from a local font file.
   - One page shows "أهلاً، <full name>".
5. **Tests:**
   - one passing Python test in `construction_core/tests/test_smoke.py`
   - one Playwright test that logs in and sees the greeting
6. **CI (GitHub Actions, free for private repos within the monthly minutes)**, on every push:
   - run MariaDB and Redis services
   - `bench init` (version-16), get erpnext, and install our app on a fresh site
   - run `bench run-tests --app construction_core`

   Keep Playwright local if it makes CI too slow, and document that.

## Acceptance criteria
- [ ] `docs/versions.md` lists the exact versions and licenses.
- [ ] `http://inceptiondesign.localhost:8000/portal` shows the Arabic RTL greeting after login, and redirects to `/login` when logged out.
- [ ] `bench run-tests --app construction_core` passes locally.
- [ ] CI is green on `main`.
- [ ] No secret is in git: `git grep -iE "password|secret|token"` shows only `.env.example` keys.

## Out of scope
Any DocType, any server or domain.
