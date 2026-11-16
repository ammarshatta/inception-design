# Versions and licenses

**Recorded on:** 16 Nov 2026, in the Claude cloud session. Upstream `git ls-remote` and source checkouts were used to read these values; nothing was installed.

**Still to do on the owner's computer:** run `bench version` and replace the "Installed" column with what the bench really has.

| Component | Branch | Latest tag on 16 Nov 2026 | Version in branch source | Installed (`bench version`) | License |
|---|---|---|---|---|---|
| frappe | `version-16` | v16.56.0 | 16.56.0 (commit 49789a1, 2026-11-10) | _fill in locally_ | MIT |
| erpnext | `version-16` | v16.55.0 | 16.55.0 (commit 8e10a34, 2026-11-12) | _fill in locally_ | GPL-3.0 |
| frappe_docker | `main` | v4.2.0 | commit 0ad1a11 | _fill in locally_ | MIT |
| frappe-ui (npm) | n/a | repo version 1.2.0 (2026-11-13) | the starter pins `^0.1.261`; `yarn.lock` decides the exact version | _fill in from `frontend/yarn.lock`_ | MIT |
| frappe-ui-starter | `main` of `github.com/frappe/frappe-ui-starter` | commit 0088f92 (2026-03-31) | copied into `frontend/` on 16 Nov 2026 | n/a | MIT |
| IBM Plex Sans Arabic | `IBM/plex` repo | woff2 files in `frontend/src/assets/fonts/` | Regular, Medium, SemiBold, Bold | n/a | SIL Open Font License 1.1 (`OFL-LICENSE.txt`) |

## Reference projects (read only, nothing copied)

- **Quantbit Construction Management**: a Frappe app for construction projects. It is a reference for ideas only.
- **BuildSuite**: a construction ERP on Frappe. It is a reference for ideas only.

Frappe Helpdesk, CRM and Press are AGPL-3.0. They must not become dependencies (CLAUDE.md rule 15).

## Notes

- The portal uses the current `frappe/frappe-ui-starter`, not the older `netchampfaris/frappe-ui-starter`. That one was last updated in 2023 and pins frappe-ui 0.0.105.
- frappe-ui 1.x exists. Upgrading from the starter's 0.1.x is a separate task. Do it only after phase 0 works.
