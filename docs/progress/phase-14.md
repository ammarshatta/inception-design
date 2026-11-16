# Phase 14 — Documents, photo markup and takeoff

**Status:** 🟢 Unit tests green in CI (run 43975747126, 17 Nov 2026). Playwright results are recorded in PROGRESS.md as they come in.

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate.

## What was built

| Task | Where |
|---|---|
| **Project Document** (+ Document Version): folders عقود / رسومات / مواصفات / تصاريح / فواتير / أخرى, client-visible flag, versions with uploader, time and SHA-256; old versions cannot be edited or removed | `doctype/project_document`, `documents.upload_version` |
| Client sees only visible documents and only the current version. A **File permission hook** blocks older versions and hidden documents even with the direct `/private/files/...` URL | `documents.file_has_permission`, `permissions.py` |
| Download history: every open goes through `download_url`, which writes a Frappe **Access Log** entry | `documents.download_url` |
| Signed contracts (phase 8) are added automatically to "عقود", visible to the client (subcontracts stay internal) | `documents.add_signed_contract`, called from `esign.sign` |
| Search by title or folder within a project | `documents.project_documents` |
| Portal pages: engineer `/portal/projects/<p>/documents` (upload new document or version, old versions), client `/portal/c/<p>/documents` | `DocumentsPage.vue` |
| **Markup**: arrow, circle, rectangle, pen, Arabic text, 4 colours, undo. Shapes saved as JSON (validated and limited on the server), a flattened private PNG saved next to it; the original file is only read. Re-opening loads the editable shapes | `doctype/markup`, `documents.save_markup`, `MarkupPage.vue`; "ارسم" on every photo in the stage page |
| **Takeoff**: open a PDF (pdf.js 3.11.174, Apache-2.0, `isEvalSupported: false`) or an image; calibrate with a line of known length; length (polyline), area (polygon, shoelace) and count. The server recomputes every value from the points | `doctype/takeoff`, `takeoff.py`, `TakeoffPage.vue` |
| "أضف للتسعير": the measured value becomes the quantity of a chosen line, or a new line, of a draft Estimate; button "قياس من الرسم" on the Estimate form | `takeoff.push_to_estimate`, `public/js/estimate.js` |

No library was added for markup: it is plain SVG + canvas, so there is nothing to license or update. pdf.js is the only new dependency (Apache-2.0, free).

## Not done

- Markup on PDF pages (markup works on images; PDFs are measured in the takeoff page only).
- Multi-page PDFs in the takeoff page: page 1 only.
- A desk (`/app`) markup editor: markup is in the portal, which office staff can also open.

## Decisions to review

1. pdf.js 3.11.174 is used with `isEvalSupported: false`, which closes the known issue in that line (CVE-2024-4367). Moving to pdf.js 4 needs a newer build target; it can be done later.
2. Takeoff is office-only (Construction Sales / Admin), as estimating is.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Area and length: 4×5 m rectangle at a known scale = 20 m²; L-shape polygon | `test_documents.TestGeometry` | ✅ CI |
| New version keeps the old one downloadable; client sees the current one only | `test_versions_and_client_visibility` | ✅ CI |
| Markup saves and re-opens with editable shapes; original unchanged (hash) | `test_markup_keeps_original` | ✅ CI |
| Playwright: calibrate, measure an area, push it to an estimate line | `e2e/takeoff.spec.ts` | pending CI |
| A client cannot download a non-visible document even with its URL | `test_versions_and_client_visibility` (File permission) | ✅ CI |
| P14-04 AC2: measured area becomes an estimate line's quantity | `TestTakeoffToEstimate` + e2e | ✅ CI |
