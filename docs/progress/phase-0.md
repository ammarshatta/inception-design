# Phase 0 — Local foundation

**Status:** ✅ Verified in CI on 16 Nov 2026, run [43934298054](https://github.com/ammarshatta/inception-design/actions/runs/43934298054). It still needs one install on the owner's computer.

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

## CI evidence (run 43934298054, 16 Nov 2026)

| Step | Result |
|---|---|
| `bench init` (frappe version-16), get erpnext version-16 | ✓ |
| `new-site`, `install-app erpnext`, `install-app construction_core`, `migrate` | ✓ no errors |
| `run-tests --app construction_core` | ✓ `Ran 33 tests … OK` |
| `bench version` | frappe 16.56.0 (49789a1), erpnext 16.55.0 (8e10a34) |
| `bench build --app construction_core` (vite build of the portal) | ✓ `www/portal.html` created |
| Playwright against `bench serve` | ✓ `2 passed`. Logged out → `/login?redirect-to=/portal`. Logged in → `<html lang="ar" dir="rtl">` and "أهلاً، عميل التجربة" |

### Fixes found by running in CI
1. **Welcome emails:** ERPNext's `Project.validate` emails every new project user, and that fails when there is no outgoing email account. The test factory now marks users as welcomed.
   - **Phase 2 must handle this**, by setting up an email account or by controlling `welcome_email_sent`. Otherwise adding a client to a project fails on a site with no email.
2. **`frappe.get_doc()` never checks permissions in Python.** The tests now check what the browser actually uses: `frappe.client.get`, `check_permission`, and `get_list`.
3. **Wrong output folder:** the starter's `vite.config.js` resolved the app name one folder too high (`apps/www/portal.html`). The path is now fixed.
4. **Office-name fallback:** with an empty Settings, the office name showed "Frappe". It now falls back to the default ERPNext company.

## Not done yet

- [ ] Install on `inceptiondesign.localhost` (`docs/LOCAL-SETUP.md`, step 6) and open `/portal` once.
- [ ] Optional: upgrade frappe-ui from 0.1.x to 1.x, as a separate task.

## Acceptance criteria

| Criterion | CI / cloud | Verified on the owner's computer |
|---|---|---|
| `docs/versions.md` lists the exact versions and licenses | ✅ installed versions from CI `bench version` | ☐ |
| `/portal` shows the Arabic RTL greeting after login, and redirects to `/login` when logged out | ✅ Playwright in CI, 2 passed | ☐ |
| `bench run-tests --app construction_core` passes locally | ✅ in CI (33 OK). Local not run yet. | ☐ |
| CI is green on `main` | ✅ [run 43934298054](https://github.com/ammarshatta/inception-design/actions/runs/43934298054) | ✅ |
| No secret in git (`git grep -iE "password\|secret\|token"` shows only `.env.example` keys) | See the note below | ☐ |

**Stories:**
- **P00-01 (CI):**
  - AC1: written.
  - AC2: GitHub marks a failing run red by default.
- **P00-02 (portal):** AC1 and AC2 are written and covered by `e2e/portal.spec.ts`.
- **P00-03 (versions):** done, except the installed column.

**Note on the secrets check:** `git grep` also matches harmless code words, such as `csrf_token` and the test-only password in `before_tests`. That password is only used on throwaway CI sites. Review the list by eye.
