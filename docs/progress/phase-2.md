# Phase 2 — Admin screens and client onboarding

**Status:** 🟢 Unit tests green in CI (run 43975747126, 17 Nov 2026). Playwright results are recorded in PROGRESS.md as they come in.

**Approval:** on 16 Nov 2026 the owner asked for every phase to be built without waiting for approval between phases, with one review at the end. CI is the gate between phases.

## What was done

| Task | Where |
|---|---|
| Workspace "المقاولات" with shortcuts: projects, stages, templates, catalog, leads, payments, purchase invoices, messages, settings | `construction_core/workspace/المقاولات/` |
| Phase Template: weight total under the table, with a warning when it is not 100 | `public/js/phase_template.js` |
| Project → "المراحل" section: table of stages (weight, progress, status, dates), move up and down, add stage, total and warning | custom fields `stages_section` and `stages_html`, `public/js/project.js`, `api/admin.py` (`get_project_stages`, `move_stage`) |
| "إضافة عميل" dialog (in the "الفريق" menu) | `project.js`, `api/admin.add_client` |
| — Customer, Contact and portal User (Website User, Construction Client role) are created or linked, the user is added to Project User, and `Project.customer` is set | |
| — With email: Frappe's standard welcome email with a set-password link | |
| — Without email: a 12-character temporary password and `must_change_password = 1`. The credentials are shown once, with a wa.me button and an Arabic message. | |
| "إضافة مهندس" (only users with the engineer role) | `api/admin.add_engineer`, `engineer_query` |
| Publishing: "لينك جديد" stores only the SHA-256 of `token_urlsafe(16)`, shows the link once, and the old link stops working | `api/admin.new_share_link`, `sharing.py` |
| "معاينة بعين الزائر": `/p/<project>?t=…` shows a placeholder until phase 5, and returns 404 for an invalid, revoked or expired link | `www/public_project.*` |
| Forced password change: a `before_request` hook allows only the change-password page; the flag is cleared once the password changes; clients then go to `/portal` | `auth.py`, override of `update_password` |
| Login settings: signup disabled, username login on, 5 attempts, 900 s lockout; any Social Login Key set to "Allow" signups is reset to "Deny" | `setup/install.apply_login_settings` (runs after install and after every migrate) |
| Social login: no new accounts | `auth.py` |

**How the social-login protection works:**
- Frappe v16 already refuses OAuth signups when signup is disabled (`utils/oauth.get_user_record`, `SignupDisabledError`).
- We add two things on top:
  1. a wrapper on the Google and Facebook callbacks that shows "الحساب ده مش مسجّل، كلّم المكتب"
  2. a `User.before_insert` guard while an OAuth login is in progress

**ERPNext welcome email:** when there is no outgoing email account, new team rows are marked as welcomed, so adding users does not fail (`overrides/project.before_validate`).

## Decisions to review

1. **Clients without email:** Frappe requires an email on every User, so the user is stored as `<username>@no-email.invalid`. `.invalid` is a reserved domain, so nothing is ever delivered there. The client logs in with the username.
2. **"نسخ اللينك":** the full link is copyable only in the dialog right after "لينك جديد", because only its hash is stored. To share it again later, make a new link.
3. **Client cannot change password:** a client with a temporary password who calls the portal API gets 403 until they change it.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Timed manual run: create a project from a template, add one client with email and one with username, publish by link, all in under 3 minutes | Needs the owner on a real site | ☐ (owner) |
| Playwright: a temporary password shows only the change-password page, then reaches `/portal` | `e2e/portal.spec.ts`, 3rd test (CI) | pending CI |
| Unit test: the OAuth path cannot create a new user | `test_auth_sharing.TestNoOAuthSignup` | ✅ CI |
| After "لينك جديد" the old token is invalid; expired and private links fail | `test_auth_sharing.TestShareLinks` | ✅ CI |
| P02-01: reorder stages, and the total updates | `test_onboarding.TestStagesOrdering` | ✅ CI |
| P02-02: client with email; invalid mobile rejected | `test_client_with_email`, `test_mobile_validation` | ✅ CI |
| P02-03: client without email gets a 12-character password and a wa.me link | `test_client_without_email` | ✅ CI |
| P02-05: an added engineer sees the project | `test_add_engineer` | ✅ CI |
