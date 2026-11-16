# Phase 1 — Data model and permissions

## Goal
All DocTypes and custom fields from `00-overview.md` exist, and project-level permissions are enforced and proven by tests.

## Tasks

1. **DocTypes** (module "Construction Core"), exactly as listed in `00-overview.md`:
   - Arabic labels.
   - Currency for money fields.
   - Every Attach field is uploaded as **private**.
   - Turn on `track_changes` for `Project Stage` and `Payment Milestone`.
   - Create the single DocType `Inceptiondesign Settings`, with the feature flags.
     - Every template, email and page reads the office name, logo and colors from it (SaaS rule, `CLAUDE.md` rule 15).
     - Add a test that fails if the office name appears hardcoded in `construction_core` (grep on templates and Python).
2. **Custom fields** on `Project`, `User`, `Purchase Invoice` and `Lead`, exported as fixtures together with the roles and Custom DocPerms. Turn on Track Changes for `Project` via Property Setter.
3. **Roles:** `Construction Admin`, `Construction Engineer` (desk access off — they use `/portal`), `Construction Client`.
4. **Permissions** in `permissions.py`, registered in `hooks.py`:
   - `has_permission` and `permission_query_conditions` for `Project`, `Project Stage`, `Stage Update`, `Payment Milestone` and `Project Message`.
     - Rule: the user is in the project's `Project User` table, or has Construction Admin or System Manager.
     - One helper, `assert_project_access(project, ptype="read")`, used by every API method.
   - Clients:
     - never get `Stage Update` with `internal_only = 1`, in single reads or in lists
     - can create `Project Message` only of kind Text
     - can change only the answer fields of an Approval addressed to their project
   - `Design Template` gives no Guest permission. Public access goes only through `api/public.py` (phase 5).
5. **Server logic** (controllers or doc_events):
   - **`Project Stage.validate`:** in Auto mode, progress = done items ÷ all items × 100. With zero items, progress = 0.
   - **`Project Stage.on_update`:**
     - recompute `Project.weighted_progress`
     - when the status becomes Done, set `actual_end` and move that stage's `Payment Milestone` records from Upcoming to Due
   - **`Project.after_insert`:** if `phase_template` is set, copy its stages and checklist lines into `Project Stage`.
   - **`Stage Update.after_insert`:** if the stage is Manual and `progress_after` is set, update the stage's progress.
   - **`Project Message.validate`:** once `approval_status` is not Pending, reject any further change, even from Administrator.
6. **Test data factory** in `construction_core/tests/factories.py`:
   - creates: an admin, 2 engineers, 2 clients, a "تشطيب شقة" template with 8 stages, and 2 projects
   - used only by tests; never installed by fixtures

## Required tests (`bench run-tests --app construction_core`)
- [ ] An engineer not in `Project User`:
  - `frappe.get_doc("Project", p)` raises PermissionError
  - `frappe.get_list` does not return it
- [ ] The same for a client on another client's project, and for `Stage Update`, `Payment Milestone` and `Project Message`.
- [ ] A client cannot read an `internal_only` update, by single get or by list.
- [ ] Weights example:
  - stage A, weight 5, Done (100%)
  - stage B, weight 30, at 50%
  - the remaining weights at 0%
  - total = **20.0%**
- [ ] An Auto stage with 3 of 4 items done = 75%.
- [ ] Editing the template after creating a project leaves the project's stages unchanged.
- [ ] A stage set to Done moves its milestone to Due.
- [ ] Changing an answered approval fails, even as Administrator.

## Acceptance criteria
All the tests above pass, and `bench --site <fresh site> install-app construction_core` followed by `bench migrate` runs with no errors.
