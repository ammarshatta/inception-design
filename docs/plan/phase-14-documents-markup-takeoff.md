# Phase 14 — Documents, photo markup and takeoff

## Goal
Every project has an organized document library with versions and client visibility. Engineers can draw on photos and plans, and the office can measure lengths and areas from drawings to fill estimates.

Projul equivalents: documents and files, photo markup, and field takeoffs.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Project Document` | normal | project, folder (Select: عقود, رسومات, مواصفات, تصاريح, فواتير, أخرى), title, current_version, client_visible, versions (table: `Document Version`) |
| `Document Version` | child | version_no, file (private), uploaded_by, uploaded_on, note, sha256 |
| `Markup` | normal | reference (Stage Update Media row, Project Document version, or Daily Log photo), base_file, overlay_json (shapes), rendered_file (PNG), author |
| `Takeoff` | normal | project or estimate, drawing (Project Document version), page, scale_px_per_m, measurements (table: `Takeoff Measurement`) |
| `Takeoff Measurement` | child | label, kind (Length / Area / Count), points_json, value, uom, estimate_line |

## Tasks

1. **Document library:**
   - Folders, upload new version (the old one is kept), and a download history.
   - A "client_visible" toggle.
   - The portal shows the client only visible documents, at their current version.
   - Contracts signed in phase 8 are added here automatically.
2. **Photo and plan markup** (portal and desk):
   - A canvas editor (Konva or Fabric.js, both MIT) with arrow, circle, rectangle, free draw, text in Arabic, and colors.
   - It saves `overlay_json` and a flattened PNG; the original is never changed.
3. **Takeoff:**
   - Open a PDF page (pdf.js, Apache-2.0) or an image.
   - Calibrate the scale by drawing a line of known length.
   - Measure polylines (length), polygons (area, using the shoelace formula) and counts.
   - "أضف للتسعير" pushes the measurement as qty into a phase 7 Estimate Line.
4. **Search:** documents are searchable by title and folder within a project.

## Acceptance criteria
- [ ] Area and length unit tests: a 4×5 m rectangle at a known scale = 20 m², and an L-shape polygon.
- [ ] Uploading a new version keeps the old one downloadable, and the client always sees the current one only (test).
- [ ] A markup saves and re-opens with editable shapes; the original file is unchanged (hash test).
- [ ] Playwright: calibrate, measure an area, and push it to an estimate line.
- [ ] A client cannot download a non-visible document even with its URL (test).
