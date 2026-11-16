# Phase 3 — Engineer portal

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

## What was done

| Task | Where |
|---|---|
| Portal API (`my_projects`, `project_detail`, `stage_detail`, `toggle_checklist_item`, `create_stage_update`, `attach_media`, `set_media_publishable`). Every project-scoped method calls `assert_project_access` first. | `api/portal.py` |
| Screens (Vue, RTL, 360 px first): My projects, Project, Stage (checklist and updates), New update | `frontend/src/pages/` |
| Browser upload pipeline: photos resized to 1600 px and JPEG 0.8 (which drops EXIF/GPS); files uploaded one at a time, privately, with a progress bar each, 3 attempts, and a retry button | `frontend/src/lib/media.ts`, `lib/api.ts`, `pages/NewUpdate.vue` |
| Server safety net: if a photo arrives over 500 KB, over 1600 px or with any EXIF, it is re-encoded on the server | `media.py`, `sanitize_photo` |
| Videos: rejected in the browser with an Arabic message when over 50 MB or 60 s; the server checks size too; `max_file_size` = 52428800 | `media.ts`, `attach_media`, `setup/install.apply_site_config` |
| "مناسبة للنشر": creates a separate **public** copy (`public_file`); turning it off deletes the copy; the original stays private | `media.make_public_copy` |
| PWA: manifest (name from Settings), icons, and a service worker that caches `/assets/` only and never `/api` (`Service-Worker-Allowed: /portal/`) | `api/public.py`, `public/pwa/`, `main.ts` |

## Decisions

1. **The service worker and manifest are served by `api/public.py`.** Frappe does not serve `.js` files from `www/`, and the service worker needs the `Service-Worker-Allowed` header to control `/portal/`.
2. **The client home page still shows only the greeting.** The client portal is phase 4.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Playwright on Slow 4G: 10 photos of 4 MB or more upload, and the update shows 10 | `e2e/engineer.spec.ts` (CI) | ✅ CI |
| Each stored photo is under 500 KB with no GPS. Checked by downloading every file and checking for an EXIF block; a server unit test checks the GPS IFD. | `engineer.spec.ts`, `test_engineer_portal.test_photo_is_resized_and_stripped` | ✅ CI |
| A private file URL is not served to a logged-out browser | `engineer.spec.ts` | ✅ CI |
| `project_detail` on another engineer's project → permission error | `test_project_detail_other_project_denied` | ✅ CI |
| Screens usable at 360 px (screenshots) | CI artifact `screenshots`, copied to `docs/progress/screens/phase-3/` | ✅ CI |
| P03-03: ticking an item updates stage and project progress | `test_toggle_checklist_updates_progress` | ✅ CI |
| P03-04: the client never sees internal updates | `test_client_stage_detail_hides_internal` | ✅ CI |
| P03-05: a public copy is made and removed | `test_publishable_makes_public_copy` | ✅ CI |
| P03-06: the video limit message | `engineer.spec.ts`, 2nd test | ✅ CI |
| P03-07: installable on Android Chrome | manifest and service worker tested; the install itself needs a real phone | ☐ (owner, at the end) |
