# Phase 1 — Data model and permissions

**Status:** ✅ All required tests pass in CI on a fresh ERPNext v16 site, run [43934298054](https://github.com/ammarshatta/inception-design/actions/runs/43934298054), 16 Nov 2026.

## Plan

Implement everything in `docs/plan/phase-01-data-permissions.md`:
- DocTypes, custom fields, roles and permissions
- server logic
- a test data factory
- the required tests

## What was done (cloud)

### DocTypes (module "Construction Core")

All of them have Arabic labels. The generator script is not in the repo; the JSON files are the source of truth.

| DocType | Type | Notes |
|---|---|---|
| Phase Template (+ Phase Template Stage) | normal + child | `total_weight`; warns when the total is not 100 |
| Project Stage (+ Stage Checklist Item) | normal + child | track_changes on. Auto/Manual progress. Checklist rows get stamped with who ticked them and when. `actual_start` and `actual_end` are set from the status. |
| Stage Update (+ Stage Update Media) | normal + child | `internal_only`. The stage must belong to the project. |
| Payment Milestone | normal | track_changes on. Statuses: Upcoming, Due, Invoiced, Paid. Added a `due_date` field for the payments screen. |
| Project Message | normal | Text or Approval. Added an `answer_note` field so the client can write a question. |
| Design Template (+ Design Media) | normal + child | slug validation. No Guest permission. |
| Inceptiondesign Settings | single | Office name, logo, colors, WhatsApp number, terms, default engineer, and 5 feature flags |

### Fixtures (`construction_core/fixtures/`)

- **Roles:**
  - Construction Admin (desk on)
  - Construction Engineer (desk **off**)
  - Construction Client (desk off)
- **Custom fields:**
  - **Project:** every field listed in `00-overview.md`
  - **User:** `must_change_password`
  - **Purchase Invoice:** `project_stage`
  - **Lead:** `design_template`, `apartment_area_m2`, `governorate`
- **Property Setter:** Project `track_changes` = 1.

### Our roles' rights on ERPNext's Project

These are given in code by `setup/install.py`, which runs after install and after every migrate.

They are not exported as Custom DocPerm fixtures. Exporting them would replace ERPNext's standard Project permissions for every other role. `add_permission` copies the standard rules first.

### Permissions (`construction_core/permissions.py`, registered in `hooks.py`)

- `has_permission` and `permission_query_conditions` for Project, Project Stage, Stage Update, Payment Milestone and Project Message.
- **Scoped users** are Construction Engineer or Construction Client users without a full-access role.
  - They see a project only when they are in its `Project User` table.
  - Full-access roles are System Manager and Construction Admin.
- **Other desk roles** (for example an accountant) keep ERPNext's normal access. This is a decision; check it.
- **Clients:**
  - never see `internal_only` updates, whether by single read or by list
  - can create only Text messages
  - can change only `approval_status` and `answer_note` on an approval
- **`assert_project_access(project, ptype="read")`** is the helper every API method uses.

### Server logic

| Rule | Where |
|---|---|
| Auto progress = done ÷ all × 100; 0 with no items | `project_stage.py`, `auto_progress` |
| Project progress = Σ(weight × progress) ÷ Σ(weight), stored in `Project.weighted_progress` | `project_stage.py`, `update_project_progress` |
| When a stage becomes Done: set `actual_end`, and move its Upcoming milestones to Due | `project_stage.py` |
| Copy the template's stages and checklists when a project is created; this is a snapshot | `overrides/project.py` |
| A Stage Update with `progress_after` > 0 on a Manual stage sets the stage's progress | `stage_update.py` |
| An answered approval cannot be changed or deleted, even by Administrator | `project_message.py` |
| Warning on the Project form when the weights do not total 100 | `public/js/project.js` + `get_weight_summary` |
| Every file attached to our DocTypes is private, except the Settings logo | `overrides/file.py` |
| Branding helper, also exposed to Jinja | `branding.py` |

### Tests (33 in total, in `construction_core/tests/`)

| File | Tests |
|---|---|
| `test_permissions.py` | 13 |
| `test_progress.py` | 11 |
| `test_approvals.py` | 4 |
| `test_branding.py` | 2 |
| `test_smoke.py` | 3 |

The data comes from `factories.py`:
- an admin, 2 engineers and 2 clients
- the "تشطيب شقة" template with 8 stages whose weights total 100
- 2 projects

## Decisions to review

1. **`progress_after`:** it counts as "set" only when it is above 0. Frappe stores an empty Percent as 0, so 0 cannot be told apart from empty.
2. **Engineer role:** it has desk access off, as `phase-01` says. The roles table in `00-overview.md` says "System User". Change it in `fixtures/role.json` if engineers should open `/app`.
3. **Accountants and other ERPNext roles:** they are not limited by project membership.
4. **Settings logo:** it stays public so public pages can show it. All other attachments are private.

## Not done yet

- [ ] Install once on your own site (`docs/LOCAL-SETUP.md`, step 6).
- [ ] Review the 4 decisions above.

**Note for phase 2:** adding a user to a project triggers ERPNext's welcome email (see `phase-0.md`, CI fixes).

## Required tests and acceptance criteria

| Requirement | Test | CI result | Verified locally |
|---|---|---|---|
| An engineer not in Project User gets PermissionError on get_doc, and the project is not in get_list | `test_engineer_cannot_read_other_project` | ✅ pass | ☐ |
| The same for a client and for Stage Update, Payment Milestone and Project Message | `test_client_cannot_read_other_clients_*`, `test_engineer_cannot_read_other_project_records` | ✅ pass | ☐ |
| A client cannot read an internal_only update, by get or by list | `test_client_cannot_read_internal_update` | ✅ pass | ☐ |
| Weights example = 20.0% | `test_weighted_progress_example`, `test_project_progress_example` | ✅ pass | ☐ |
| Auto stage, 3 of 4 done = 75% | `test_auto_progress`, `test_auto_stage_three_of_four` | ✅ pass | ☐ |
| Editing the template does not change the project | `test_template_edit_does_not_change_project` | ✅ pass | ☐ |
| A Done stage moves its milestone to Due | `test_done_stage_moves_milestone_to_due` | ✅ pass | ☐ |
| An answered approval cannot be changed, even by Administrator | `test_client_answers_then_locked_even_for_administrator` | ✅ pass | ☐ |
| Weights ≠ 100 shows a warning (P01-03, AC3) | `test_weight_warning` + `project.js` | ✅ pass | ☐ |
| Branding comes from Settings, and no office name or phone is hardcoded (P01-05) | `test_branding.py` | ✅ pass | ☐ |
| `install-app` + `migrate` run on a fresh site without errors | CI Install step | ✅ pass | ☐ |
