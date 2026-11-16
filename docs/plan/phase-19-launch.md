# Phase 19 — Hosting, compliance and launch

## Goal
The finished platform moves from the owner's computer to a hosted server and goes live, with:
- HTTPS on the real domain
- encrypted daily off-site backups and a tested restore
- Google and Facebook login
- a one-command deploy for future updates

This is the first phase that costs money.

## Owner provides first (see `hosting-options.md`)
- The hosting choice: a VPS (recommended, Ubuntu 24.04, 8 GB RAM or more) or Frappe Cloud.
- The domain, added to Cloudflare.
- A Cloudflare R2 bucket named `inceptiondesign-backups` and its access key.
- Brevo SMTP credentials.
- A Google OAuth client, with the consent screen set to "In production".
- A Meta app with the permissions `public_profile` and `email`.
- If online payments are switched on: a live merchant account with the payment gateway, and the owner's written approval of its fees.
- If the AI assistant is switched on: the provider API key and the monthly cap.
- **The answers from a lawyer on the data-protection checklist below**, including the decision on where data may be hosted.

Stop and ask for anything missing.

## Data-protection checklist (Egypt PDPL 151/2020 — the owner confirms with a lawyer)

The executive regulations took effect on 1 Nov 2025, with a one-year grace period, so enforcement is expected from about 1 Nov 2026. The points to settle before launch:

- [ ] **Licence:** does the office need a controller licence from the Personal Data Protection Center? Fees depend on database size, and smaller databases can be exempt.
- [ ] **Data location:** storing client data on a server outside Egypt (EU VPS, R2) counts as a cross-border transfer, which needs a licence. Choose one:
  - get the transfer licence
  - or host in Egypt (see `hosting-options.md`) and keep backups in Egypt
- [ ] **DPO:** appoint a Data Protection Officer if required.
- [ ] **Notices and consent:** an Arabic privacy notice on `/privacy`, and consent records for GPS clock-in and marketing.
- [ ] **Breach plan:** notify the regulator within 72 hours and the affected people soon after. Write `docs/breach-plan.md` with who does what.
- [ ] **Register of processing:** a list of what personal data is stored, why, and for how long, in `docs/data-register.md`.

## Tasks (VPS — for Frappe Cloud, follow its own deploy flow and skip 1–3, 8–9)

1. **Server hardening:**
   - a non-root sudo user; SSH by key only, with root login off
   - `ufw` allowing only 22, 80 and 443
   - `unattended-upgrades`, 2 GB of swap, and time zone Africa/Cairo
2. **Custom image:**
   - Build a frappe_docker custom image with frappe, erpnext and construction_core at pinned versions, following frappe_docker's custom-apps guide (`apps.json`). Store `apps.json` in `deploy/`.
   - Push the image to GitHub Container Registry (private).
3. **Stack:** frappe_docker `compose.yaml` plus overrides for MariaDB, Redis and the HTTPS proxy, all in `deploy/`, with `deploy/.env.example`.
4. **Production site:**
   - Arabic, EGP, Africa/Cairo, and one company.
   - `max_file_size` = 52428800.
   - A strong admin password, kept by the owner and never in git.
   - **No** `developer_mode` and **no** `ignore_csrf`.
5. **Moving data from local** (only what the owner wants live: real designs, templates, settings):
   - Export the records as fixtures or with data import.
   - **Never** copy the whole local database with test users onto production.
6. **Cloudflare:**
   - DNS proxied; SSL "Full (strict)"; WebSockets on.
   - **A Cache Rule with "Bypass cache" for:**
     - `/api/*`, `/app*`, `/portal*`
     - `/private/*`, `/p/*`
     - `/login*`, `/update-password*`

     This keeps private client photos out of the public cache.
7. **Email:** Brevo SMTP as the default outgoing Email Account.
8. **Backups:** `deploy/backup.sh`, run by cron daily at 03:00. It:
   - runs `bench --site <site> backup --with-files`
   - encrypts the backup with rclone crypt; the key is kept by the owner in two places off the server
   - uploads it to R2
   - deletes copies older than 30 days
   - emails the owner on failure
9. **Deploy:** `deploy/deploy.sh <tag>`. It:
   - takes a backup
   - pulls the image
   - restarts the containers
   - runs `bench migrate`
   - checks `/api/method/ping`
   - rolls back to the previous tag on failure

   A GitHub Actions job builds and pushes the image when a tag `vX.Y.Z` is pushed.
10. **Social login:**
    - Add Social Login Keys for Google and Facebook.
    - Test that a registered client's email logs in and an unknown email is refused.
11. **Monitoring (free):**
    - an external uptime check that emails when the site is down
    - a cron job that emails when the disk is over 80% or no backup was made that day
12. **Security review:** a table in `docs/progress/phase-19.md` that:
    - lists every `@frappe.whitelist` method and how it checks access
    - confirms `allow_guest` appears only in `api/public.py`
    - lists every `ignore_permissions=True`, each with a justifying comment in the code
13. **Load check:**
    - Simulate 20 concurrent portal users (k6 or Locust, run from the owner's machine).
    - Record the response times and server RAM.
    - Report if RAM goes above 85%.
14. **Docs:**
    - `docs/deploy.md`, `docs/restore.md`, `docs/licenses.md`, `docs/known-limitations.md`
    - a one-page Arabic `docs/owner-guide.md`
15. **Switch on live integrations,** one at a time and each tested:
    - **Payment gateway:** live keys, webhook URL, and a real small payment refunded.
    - **Web Push:** VAPID keys.
    - **AI provider:** key and cap.
    - **GPS clock-in:** consent text approved by the owner.
16. **Clean up:** run the demo removal command and confirm there are no test users or records.
17. **Go live:** tag `v1.0.0`, deploy it, and turn on the uptime alerts to the owner's email.

## Acceptance criteria
- [ ] `https://<domain>/app` opens in Arabic over HTTPS, and `/portal` and the public pages work.
- [ ] `curl -I` on a private file URL shows `cf-cache-status` of `BYPASS` or `DYNAMIC`, never `HIT`.
- [ ] A backup was downloaded from R2, decrypted, and restored on the owner's computer using only `docs/restore.md`. Record the steps and time.
- [ ] `deploy.sh` with a bad tag rolled back automatically (tested once).
- [ ] Google login was tested with a known and an unknown account, and Facebook with a known account.
- [ ] The security review table is complete, and the load-check results are recorded.
- [ ] Production has no demo or test data (show the queries in the report).
- [ ] Every item in the data-protection checklist is answered and recorded in the report.
- [ ] Each switched-on live integration passed its live test.
- [ ] `v1.0.0` is live and `/api/method/ping` returns OK.
