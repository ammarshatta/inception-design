# Phase 0 — Local foundation

**Status:** 🟡 Code written in the cloud session on 16 Nov 2026. **Not run yet.**

**Approval:** the owner asked to "complete what you can" (16 Nov 2026). That counts as approval of this plan for the cloud part only.

## Plan

1. Generate the app the way `bench new-app` does for v16, by running the boilerplate templates from frappe's `utils/boilerplate.py`.
   - title "Construction Core", MIT license, module "Construction Core"
2. Make the app folder the repo. Add `CLAUDE.md`, `docs/`, `.env.example` and the `.gitignore` rules.
3. Build the portal skeleton:
   - start from the current `frappe/frappe-ui-starter`
   - router base `/portal`
   - build output goes to `www/portal.html`
   - RTL and Arabic, with a local IBM Plex Sans Arabic font
   - the greeting page
4. Tests:
   - a Python smoke test
   - a Playwright test for the greeting and the login redirect
5. CI with GitHub Actions, using MariaDB, Redis, frappe and erpnext `version-16`.
6. Write `docs/versions.md`.

## What was done (cloud)

| Item | Where |
|---|---|
| App skeleton generated from frappe v16's own boilerplate templates (pyproject, hooks, modules.txt, patches, pre-commit, CI and linter workflows) | repo root, `construction_core/` |
| `required_apps = ["erpnext"]`, install, migrate and before_tests hooks | `construction_core/hooks.py`, `construction_core/setup/install.py` |
| CI uses frappe and erpnext `version-16`, installs both apps on a fresh site, migrates, then runs the tests | `.github/workflows/ci.yml` |
| `before_tests` runs the setup wizard (Egypt, EGP, Africa/Cairo) when the CI site has no company | `setup/install.py` |
| Portal at `/portal`: a route rule for sub-paths, and `www/portal.py` redirects guests to `/login?redirect-to=…` and passes the boot data | `hooks.py`, `construction_core/www/portal.py` |
| Vue portal from the current frappe-ui-starter: `lang="ar" dir="rtl"`, router base `/portal`, IBM Plex Sans Arabic from local woff2 files, greeting "أهلاً، <full name>" | `frontend/` |
| `get_me` API returning the full name, roles, branding and feature flags | `construction_core/api/portal.py` |
| Root `package.json` so `bench build` builds the portal | `package.json`, `yarn.lock` |
| Python smoke tests | `construction_core/tests/test_smoke.py` |
| Playwright tests for the redirect and the greeting (local only, not in CI) | `e2e/` |
| `.env.example` with empty values | repo root |
| Versions and licenses | `docs/versions.md` |
| Plan, backlog and design docs moved into the repo | `docs/` |

**Checks run in the cloud:**
- `python -m py_compile` on every Python file: pass
- `ruff check` and `ruff format`: pass
- every JSON file parses
- the pure functions were run with a stub of frappe: pass

**What could not be checked in the cloud:**
- No Docker, MariaDB, pip or npm installs were available there. So nothing was installed, migrated, built or tested against a real site.

## Not done yet

- [ ] Install on `inceptiondesign.localhost`, then migrate and build.
- [ ] Run the tests locally.
- [ ] Check that CI is green on GitHub.
- [ ] Fill the "Installed" column in `docs/versions.md` from `bench version`.
- [ ] Run `yarn install` in `frontend/`. The starter's `yarn.lock` is kept as it is.
- [ ] Run the Playwright tests: `cd e2e && yarn && npx playwright install chromium && E2E_USER=… E2E_PASSWORD=… yarn test`.

## Acceptance criteria

| Criterion | Cloud | Verified on the owner's computer |
|---|---|---|
| `docs/versions.md` lists the exact versions and licenses | Done from upstream sources. The installed column is still empty. | ☐ |
| `/portal` shows the Arabic RTL greeting after login, and redirects to `/login` when logged out | Code written: `www/portal.py`, `frontend/`, `e2e/portal.spec.ts` | ☐ |
| `bench run-tests --app construction_core` passes locally | Not run | ☐ |
| CI is green on `main` | Not run (the first push triggers it) | ☐ |
| No secret in git (`git grep -iE "password\|secret\|token"` shows only `.env.example` keys) | See the note below | ☐ |

**Stories:**
- **P00-01 (CI):**
  - AC1: written.
  - AC2: GitHub marks a failing run red by default.
- **P00-02 (portal):** AC1 and AC2 are written and covered by `e2e/portal.spec.ts`.
- **P00-03 (versions):** done, except the installed column.

**Note on the secrets check:** `git grep` also matches harmless code words, such as `csrf_token` and the test-only password in `before_tests`. That password is only used on throwaway CI sites. Review the list by eye.
