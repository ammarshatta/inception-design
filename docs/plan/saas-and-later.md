# SaaS path and later work

Nothing here starts without an explicit request from the owner. The **SaaS-readiness rules** at the top apply from phase 0; they are also in `CLAUDE.md`.

## SaaS-readiness rules (apply now)

1. **No single-office assumptions.**
   - Office name, logo, colors, contact details, WhatsApp number, terms and contract templates all live in a single DocType, `Inceptiondesign Settings`, plus ERPNext's `Company`.
   - Nothing is hardcoded in code or templates.
2. **One tenant = one Frappe site.**
   - Frappe already supports many sites on one bench, each with its own database. Our code must never read or write across sites.
   - Use `frappe.local.site` paths only, and no global caches keyed without the site.
3. **No AGPL dependencies without approval.**
   - Frappe's end-user apps (for example CRM, Helpdesk) and Press are AGPL-3.0.
   - We use ERPNext (GPLv3) and MIT libraries only, so licensing for a hosted service stays simple.
4. **Per-tenant configuration.** Gateway keys, email accounts and OAuth keys are per site (`site_config.json` or Settings), never per bench.
5. **Feature flags.** Phase-level features (selections, GPS, online payments, AI) can be switched on or off per site in Settings. This lets us sell plans later.
6. **Measurable usage.** Count per site: active users, projects, storage used and AI cost. These are needed for billing later.

## Licensing (not legal advice — confirm with a lawyer before selling)

| Way of selling | What it means |
|---|---|
| **Hosted SaaS** (we run it, customers use it over the web) | ERPNext is GPLv3, not AGPL. A Frappe team member said on the forum that network delivery is not "distribution" under GPL, so our app does not have to be released as GPL when only offered as a hosted service. |
| **Selling copies** customers install themselves | Distribution. `construction_core` imports ERPNext, so ship it under GPLv3 with its source. |
| **Using AGPL apps** (Frappe CRM, Helpdesk, Press) | AGPL covers network use. Using or modifying them in the SaaS can oblige us to publish our source, which is why rule 3 above exists. |

## SaaS phase (S1–S4, after the office has used the product for a while)

- **S1 — Tenant provisioning:**
  - A command and an admin screen create a new site for a customer: `bench new-site`, then install the apps, apply defaults, and set the Company and Settings.
  - Each tenant gets a subdomain, e.g. `office.inceptiondesign.com`, with wildcard DNS and a wildcard certificate.
- **S2 — Billing:**
  - Plans by feature flags and limits (users, projects, storage).
  - Monthly invoicing from our own ERPNext, and payment through the phase 15 gateway.
  - Suspend tenants with unpaid bills.
- **S3 — Operations:**
  - Per-tenant backups.
  - A `bench migrate` rollout across all sites with canary sites first.
  - A noisy-neighbor watch: CPU and RAM per site.
  - Move to multiple servers when needed.
- **S4 — Onboarding:**
  - A public signup page with a trial.
  - An Arabic onboarding wizard (company, logo, first template, first project).
  - Import from Excel.

Before S1:
- Review `frappe/press` (AGPL-3.0, powers Frappe Cloud) only as a reference.
- Do not deploy it unless the owner accepts its license.

## Later features (any time after launch)

- **Egyptian Tax Authority e-invoicing:** ask the accountant whether you are required to use it. If so, choose between a commercial ERPNext app and building our own.
- **Native App Store and Play Store apps:** wrap the PWA with Capacitor, only if the PWA is not enough.
- **Subcontractor self-service:** subcontractors submit claims through the ERPNext Supplier Portal.
- **Quality and snagging:** a defect list per unit with photos and plan pins, using phase 14 markup.
- **Warranty and after-sales:** maintenance requests after handover.
- **Frappe Builder (MIT):** marketing pages the owner edits visually.
- **Multi-currency and other countries:** for SaaS customers outside Egypt.
