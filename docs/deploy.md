# Deploying Inceptiondesign (phase 19)

> Nothing here has been run yet: it needs the owner's server, domain and accounts (phase 19 is the first phase that costs money). The files are ready in `deploy/`.

## One-time server set-up (Ubuntu 24.04 VPS, 8 GB RAM or more)

1. Hardening: a sudo user, SSH keys only, `PermitRootLogin no`; `ufw allow 22,80,443/tcp`; `unattended-upgrades`; 2 GB swap; `timedatectl set-timezone Africa/Cairo`.
2. Install Docker, `rclone` and `mailutils`.
3. `git clone https://github.com/frappe/frappe_docker` and this repository next to it.
4. `cp inception-design/deploy/.env.example inception-design/deploy/.env` and fill it in (domain, DB password, alert email). Never commit it.
5. `rclone config`: an R2 remote, then a **crypt** remote over it named as in `RCLONE_REMOTE`. Keep the two crypt passwords with the owner in two places off the server.
6. First image: push a tag (`git tag v1.0.0 && git push --tags`); the **Image** workflow builds `ghcr.io/ammarshatta/inceptiondesign:v1.0.0`. The repository is private, so the `apps.json` URL in the build needs read access: add a fine-grained read-only token as the build secret, following frappe_docker's "custom apps" guide (check `images/layered/Containerfile` options when building the first time).
7. Start the stack (command at the top of `deploy/compose.override.yaml`), then create the site:
   `bench new-site <domain> --install-app erpnext --install-app construction_core --admin-password <strong>`
   Set: language Arabic, currency EGP, time zone Africa/Cairo, one company. `max_file_size` is set by our app. Never set `developer_mode` or `ignore_csrf`.
8. Cloudflare: DNS proxied, SSL "Full (strict)", WebSockets on, and a **Cache Rule "Bypass cache"** for `/api/*`, `/app*`, `/portal*`, `/private/*`, `/p/*`, `/login*`, `/update-password*`.
9. Email: Brevo SMTP as the default outgoing Email Account (signing codes, receipts, reminders and the weekly summary need it).
10. Cron (`crontab -e` for the deploy user):
    ```
    0 3 * * * /home/<user>/inception-design/deploy/backup.sh >> /var/log/cc-backup.log 2>&1
    0 * * * * /home/<user>/inception-design/deploy/monitor.sh
    ```
11. An external uptime check (any free service) on `https://<domain>/api/method/ping`, emailing the owner.

## Every update

1. CI is green on `main`.
2. `git tag vX.Y.Z && git push --tags` → the Image workflow builds the image.
3. On the server: `deploy/deploy.sh vX.Y.Z` (backup → pull → restart → migrate → ping → automatic rollback to the previous tag on failure).

## Moving data from the local computer

Only what the owner wants live (designs, templates, settings, price library) — as fixtures or Data Import. **Never** copy the local database (it has test users and demo data). Then run `bench --site <domain> execute construction_core.setup.demo.remove`.
