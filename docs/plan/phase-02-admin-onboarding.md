# Phase 2 — Admin screens and client onboarding

## Goal
In `/app`, the admin can create a project from a template, arrange its stages, add a client and engineers, and set publishing options, with no developer help.

## Tasks

1. **Workspace "المقاولات"** with shortcuts to:
   - Projects, Phase Templates, Design Templates, Leads
   - Payment Milestones, Purchase Invoices, and the reports from phase 6
2. **`Phase Template` form:** a stages table with weights. Show the weight total under the table, and a warning if it is not 100.
3. **`Project` form** (client script and server methods):
   - **"المراحل" section:**
     - an HTML field that lists `Project Stage` records (name, weight, progress, status, dates)
     - buttons: add stage, open stage, move up or down
     - a warning when the weights are not 100
   - **"إضافة عميل" button** opens a dialog with:
     - name
     - Egyptian mobile, validated by `^01[0125][0-9]{8}$`
     - email (optional)
     - username (required when there is no email)

     On confirm, the server (one transaction):
     - creates or links `Customer` + `Contact` + `User`; the User is a Website User with the Construction Client role
     - adds the user to `Project User` and sets `Project.customer`

     Then, depending on the email:
     - **With email:** send Frappe's standard welcome email with its set-password link.
     - **Without email:**
       - generate a 12-character temporary password and set `must_change_password = 1`
       - show the credentials once
       - show a "إرسال على واتساب" button that opens `https://wa.me/20<mobile without leading 0>?text=<url-encoded Arabic message with login link, username and password>`
   - **"إضافة مهندس" button:** pick from users who have Construction Engineer; adds them to `Project User`.
   - **"النشر" section:**
     - visibility and the `public_show_*` fields
     - **"نسخ اللينك"** button
     - **"لينك جديد"** button:
       - generates `secrets.token_urlsafe(16)` and stores only its SHA-256 in `share_token_hash`
       - shows the full link once
       - revokes the old one
     - `share_expires_at`
     - **"معاينة بعين الزائر"** button: opens the public URL. The page itself is built in phase 5; until then, show a placeholder.
4. **Forced password change:**
   - A `before_request` hook redirects any request (except the password page, assets and logout) to `/update-password` while `must_change_password = 1`.
   - Clear the flag when the password changes (User `on_update`, when the password field changed).
5. **Login settings:**
   - Website Settings → Disable Signup = on.
   - System Settings → Allow Login using User Name = on.
   - Allow consecutive login attempts = 5, lockout = 900 seconds.
6. **Block self-registration by social login:**
   - Add a `User.before_insert` guard: when the insert comes from an OAuth login flow and no matching user exists, throw "الحساب ده مش مسجّل، كلّم المكتب".
   - First read `frappe/utils/oauth.py` in the installed v16. If it already refuses new users when signup is disabled, document that instead and add a test.
   - Real Google and Facebook keys are added in phase 19, because both need the public HTTPS domain.

## Acceptance criteria
- [ ] Timed manual run: create a project from a template, add one client with an email and one with a username, and publish by link — in under 3 minutes. Note the time in the report.
- [ ] Playwright: a client with a temporary password logs in, sees only the change-password page, changes the password, then reaches `/portal`.
- [ ] A unit test proves that the OAuth path cannot create a new user.
- [ ] After "لينك جديد", the old token no longer validates (unit test on the token check helper).
