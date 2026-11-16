# Phase 3 — Engineer portal (`/portal`)

## Goal
On site, an engineer opens the portal on a phone, picks a project, posts an update with photos, and ticks checklist items. Photos are small and carry no location data.

## Tasks

1. **API** in `api/portal.py`. Every method calls `assert_project_access` first:
   - `my_projects()`
   - `project_detail(project)`
   - `stage_detail(stage)`
   - `toggle_checklist_item(stage, row_name, done)`
   - `create_stage_update(project, stage, text, progress_after, internal_only)`, which returns the update name
   - `attach_media(update, file_url, kind)`
   - `set_media_publishable(update, row_name, value)`
2. **Screens**, in Vue + frappe-ui, RTL, all strings in `__()`:
   - My projects: name, progress bar, current stage, last update date
   - Project: stages with progress and status
   - Stage: checklist and recent updates
   - New update: text, progress slider (Manual stages only), "داخلي فقط" toggle, photos and videos
3. **Uploads:**
   - **Photos** are resized in the browser before upload with canvas: longest side 1600 px, JPEG quality 0.8. Re-encoding drops EXIF and GPS.
   - **Videos:** at most 50 MB and 60 seconds. Reject larger ones with a clear Arabic message. Raise `max_file_size` in site config to 52428800.
   - Upload files one at a time to `/api/method/upload_file` with `is_private=1`, attached to the `Stage Update`.
   - Show a progress bar for each file. Retry a failed file up to 3 times.
   - Never leave an update silently incomplete: if a file still fails, show it in the UI with a retry button.
4. **"مناسبة للنشر"** toggle on each photo.
5. **PWA:**
   - manifest, icons, and a service worker that caches static assets only (never `/api`)
   - installable on Android Chrome

## Acceptance criteria
- [ ] Playwright, with network throttled to Slow 4G, uploads 10 photos of 4 MB or more, and the update shows all 10.
- [ ] Every stored photo is under 500 KB, and `exiftool` finds no GPS tags.
- [ ] A private file URL opened in a logged-out browser does not return the file.
- [ ] `project_detail` with another engineer's project returns a permission error (test).
- [ ] All screens are usable at 360 px width (screenshot in the report).
