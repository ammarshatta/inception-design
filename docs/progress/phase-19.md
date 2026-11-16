# Phase 19 — Hosting, compliance and launch

**Status:** ⏸ Prepared, **waiting for the owner**. This is the first phase that costs money and needs accounts in the owner's name (CLAUDE.md rules 10 and 14), so nothing was hosted.

## Ready in the repository

| Item | Where |
|---|---|
| Image build on a tag `vX.Y.Z` → GitHub Container Registry | `.github/workflows/image.yml`, `deploy/apps.json` |
| Stack override (our image, Cairo time zone) for frappe_docker | `deploy/compose.override.yaml`, `deploy/.env.example` |
| Daily encrypted off-site backup (rclone crypt over R2), 30-day retention, email on failure | `deploy/backup.sh` |
| One-command deploy with backup, migrate, ping and automatic rollback | `deploy/deploy.sh` |
| Disk and missing-backup alerts | `deploy/monitor.sh` |
| Deploy, restore, licences, known limitations, Arabic owner guide | `docs/deploy.md`, `docs/restore.md`, `docs/licenses.md`, `docs/known-limitations.md`, `docs/owner-guide.md` |
| Breach plan and register of processing (drafts for the lawyer) | `docs/breach-plan.md`, `docs/data-register.md` |
| Security review generated from the code | below (`python scripts/security_review.py`) |

## The owner provides (stop until these exist)

- [ ] Hosting choice (VPS in Egypt or abroad, or Frappe Cloud) — depends on the lawyer's answer on data location
- [ ] Domain in Cloudflare; R2 bucket `inceptiondesign-backups` + key (or an Egyptian equivalent)
- [ ] Brevo SMTP credentials
- [ ] Google OAuth client ("In production") and Meta app (`public_profile`, `email`)
- [ ] If payments go live: Paymob live merchant account and written approval of the fees
- [ ] If the assistant goes on: provider key and monthly cap
- [ ] Lawyer's answers on the PDPL checklist (licence, data location, DPO, notices, breach plan, register)

## Security review

Security fixes found while preparing this table (17 Nov 2026):
- `sales.compare_revisions` read two estimates without a permission check → now checks read permission on both.
- `scheduling.slide_task` checked the role but not the project → now requires write access to the task's project.

Notes on the table:
- Guest methods are in `api/public.py` (rule 5) and in `auth.py`, where they **replace Frappe's own guest login endpoints** (Google/Facebook callbacks and the password update) to refuse unknown accounts and clear the forced-password flag — they are not new guest surfaces.
- `api/public.paymob_webhook` is the gateway webhook: the HMAC is checked before anything is read.
- `sitelog.clock` checks access inside `do_clock`; `sales.price_import_template` returns an empty spreadsheet template.
- Every `ignore_permissions=True` is listed with its line; most are system follow-ups after the user's own action was checked (kickoff, change-order effects, receipts, logs).

| File | Method | Guest | Access checks found in the body |
|---|---|---|---|
| `construction_core/ai/chat.py` | `send` | no | _require, _require_user |
| `construction_core/analytics.py` | `engineer_dashboard` | no | is_client |
| `construction_core/api/admin.py` | `get_project_stages` | no | _get_project |
| `construction_core/api/admin.py` | `move_stage` | no | _get_project |
| `construction_core/api/admin.py` | `add_engineer` | no | _get_project, get_roles |
| `construction_core/api/admin.py` | `add_client` | no | _get_project |
| `construction_core/api/admin.py` | `new_share_link` | no | _get_project |
| `construction_core/api/admin.py` | `engineer_query` | no | _require, _require_admin |
| `construction_core/api/admin.py` | `create_client` | no | _require, _require_admin |
| `construction_core/api/portal.py` | `get_me` | no | get_roles, has_full_access, session.user |
| `construction_core/api/portal.py` | `my_projects` | no | get_list |
| `construction_core/api/portal.py` | `project_detail` | no | assert_project_access, get_list, is_client |
| `construction_core/api/portal.py` | `stage_detail` | no | _stage_project, check_permission, is_client |
| `construction_core/api/portal.py` | `toggle_checklist_item` | no | _stage_project, check_permission |
| `construction_core/api/portal.py` | `create_stage_update` | no | assert_project_access, is_client |
| `construction_core/api/portal.py` | `attach_media` | no | _get_update_for_write |
| `construction_core/api/portal.py` | `set_media_publishable` | no | _get_update_for_write |
| `construction_core/api/portal.py` | `client_home` | no | assert_project_access, get_list |
| `construction_core/api/portal.py` | `timeline` | no | assert_project_access |
| `construction_core/api/portal.py` | `gallery` | no | assert_project_access |
| `construction_core/api/portal.py` | `payments` | no | assert_project_access, get_list |
| `construction_core/api/portal.py` | `invoice_pdf` | no | assert_project_access, check_permission |
| `construction_core/api/portal.py` | `messages` | no | assert_project_access, get_list |
| `construction_core/api/portal.py` | `send_message` | no | assert_project_access, session.user |
| `construction_core/api/portal.py` | `request_approval` | no | assert_project_access, is_client |
| `construction_core/api/portal.py` | `answer_approval` | no | assert_project_access, is_client |
| `construction_core/api/public.py` | `manifest` | **yes** | — |
| `construction_core/api/public.py` | `service_worker` | **yes** | — |
| `construction_core/api/public.py` | `list_designs` | **yes** | — |
| `construction_core/api/public.py` | `get_public_design` | **yes** | — |
| `construction_core/api/public.py` | `get_public_project` | **yes** | — |
| `construction_core/api/public.py` | `list_public_projects` | **yes** | — |
| `construction_core/api/public.py` | `request_design` | **yes** | — |
| `construction_core/api/public.py` | `sitemap` | **yes** | — |
| `construction_core/api/public.py` | `paymob_webhook` | **yes** | verify_webhook |
| `construction_core/auth.py` | `update_password` | **yes** | session.user |
| `construction_core/auth.py` | `login_via_google` | **yes** | — |
| `construction_core/auth.py` | `login_via_facebook` | **yes** | — |
| `construction_core/change_orders.py` | `request_change` | no | assert_project_access, is_client, session.user |
| `construction_core/change_orders.py` | `engineer_approve` | no | assert_project_access, is_client |
| `construction_core/change_orders.py` | `send_to_client` | no | has_full_access |
| `construction_core/change_orders.py` | `apply_credit` | no | get_roles |
| `construction_core/change_orders.py` | `project_change_orders` | no | assert_project_access, get_list, is_client, session.user |
| `construction_core/construction_core/doctype/project_stage/project_stage.py` | `get_weight_summary` | no | assert_project_access |
| `construction_core/documents.py` | `project_documents` | no | assert_project_access, get_list, is_client |
| `construction_core/documents.py` | `upload_version` | no | _require, _require_staff, _staff, assert_project_access, check_permission, session.user |
| `construction_core/documents.py` | `download_url` | no | assert_project_access, check_permission, is_client |
| `construction_core/documents.py` | `save_markup` | no | _require, _require_staff, _staff, assert_project_access, check_permission, session.user |
| `construction_core/documents.py` | `get_markup` | no | assert_project_access, check_permission |
| `construction_core/documents.py` | `markups_for` | no | _require, _require_staff, _staff, assert_project_access |
| `construction_core/esign.py` | `send_for_signature` | no | _require, _require_admin |
| `construction_core/esign.py` | `resend` | no | _require, _require_admin |
| `construction_core/esign.py` | `verify` | no | check_permission |
| `construction_core/esign.py` | `my_signature_requests` | no | session.user |
| `construction_core/esign.py` | `get_request` | no | _get_for_signer |
| `construction_core/esign.py` | `request_otp` | no | _get_for_signer |
| `construction_core/esign.py` | `sign` | no | _get_for_signer |
| `construction_core/esign.py` | `decline` | no | _get_for_signer |
| `construction_core/mcp/server.py` | `handle` | no | session.user |
| `construction_core/money.py` | `make_invoice` | no | check_permission |
| `construction_core/payments/online.py` | `start_checkout` | no | _milestone_for_client, session.user |
| `construction_core/payments/online.py` | `submit_transfer` | no | _milestone_for_client, session.user |
| `construction_core/payments/online.py` | `confirm_transfer` | no | _require, _require_accounts, session.user |
| `construction_core/payments/online.py` | `reject_transfer` | no | _require, _require_accounts, session.user |
| `construction_core/payments/online.py` | `payment_status` | no | assert_project_access |
| `construction_core/payments/online.py` | `receipt_pdf` | no | assert_project_access, check_permission |
| `construction_core/payments/online.py` | `project_payments` | no | assert_project_access |
| `construction_core/payments/online.py` | `refund` | no | get_roles, session.user |
| `construction_core/payments/reminders.py` | `todays_whatsapp` | no | has_full_access |
| `construction_core/procurement.py` | `make_material_requests` | no | _require, _require_purchasing, assert_project_access |
| `construction_core/procurement.py` | `open_deliveries` | no | assert_project_access, is_client |
| `construction_core/procurement.py` | `confirm_delivery` | no | assert_project_access, is_client, session.user |
| `construction_core/push.py` | `settings` | no | _require, _require_user, session.user |
| `construction_core/push.py` | `set_muted` | no | _require, _require_user, session.user |
| `construction_core/push.py` | `subscribe` | no | _require, _require_user, session.user |
| `construction_core/push.py` | `unsubscribe` | no | _require, _require_user, session.user |
| `construction_core/push.py` | `latest` | no | _require, _require_user, session.user |
| `construction_core/sales.py` | `price_import_template` | no | — |
| `construction_core/sales.py` | `import_prices` | no | _require |
| `construction_core/sales.py` | `estimate_from_design` | no | _require |
| `construction_core/sales.py` | `revise` | no | _require |
| `construction_core/sales.py` | `compare_revisions` | no | check_permission |
| `construction_core/sales.py` | `make_quotation` | no | _require |
| `construction_core/sales.py` | `add_followup` | no | _require, session.user |
| `construction_core/scheduling.py` | `slide_task` | no | assert_project_access, get_roles |
| `construction_core/scheduling.py` | `foreman_assignments` | no | session.user |
| `construction_core/selections.py` | `project_selections` | no | assert_project_access, get_list |
| `construction_core/selections.py` | `choose` | no | _selection_for_client |
| `construction_core/selections.py` | `approve` | no | _selection_for_client, session.user |
| `construction_core/selections.py` | `unlock` | no | has_full_access |
| `construction_core/sitelog.py` | `consent` | no | session.user |
| `construction_core/sitelog.py` | `accept_consent` | no | session.user |
| `construction_core/sitelog.py` | `clock` | no | — |
| `construction_core/sitelog.py` | `approve_clock_event` | no | assert_project_access, get_roles, session.user |
| `construction_core/sitelog.py` | `get_daily_log` | no | _require, _require_staff, _staff, assert_project_access |
| `construction_core/sitelog.py` | `save_daily_log` | no | _require, _require_staff, _staff, assert_project_access |
| `construction_core/sitelog.py` | `client_daily_logs` | no | assert_project_access |
| `construction_core/sitelog.py` | `week_summary` | no | assert_project_access |
| `construction_core/subcontracts.py` | `send_for_signature` | no | _require, _require_admin |
| `construction_core/subcontracts.py` | `pay_advance` | no | _require, _require_admin |
| `construction_core/subcontracts.py` | `release_retention` | no | get_roles, has_full_access |
| `construction_core/subcontracts.py` | `new_claim` | no | assert_project_access |
| `construction_core/subcontracts.py` | `subcontract_status` | no | _require, _require_admin, assert_project_access |
| `construction_core/sync.py` | `apply` | no | session.user |
| `construction_core/takeoff.py` | `save_takeoff` | no | _require, _require_office, check_permission |
| `construction_core/takeoff.py` | `get_takeoff` | no | _require, _require_office, check_permission |
| `construction_core/takeoff.py` | `push_to_estimate` | no | _require, _require_office, check_permission |

107 whitelisted methods; guest methods only in: ['construction_core/api/public.py', 'construction_core/auth.py']

| File | Line | Code |
|---|---|---|
| `construction_core/ai/chat.py` | 41 | `conv.insert(ignore_permissions=True)` |
| `construction_core/ai/chat.py` | 129 | `conv.save(ignore_permissions=True)` |
| `construction_core/ai/client.py` | 70 | `).insert(ignore_permissions=True)` |
| `construction_core/api/admin.py` | 186 | `user.flags.ignore_permissions = True` |
| `construction_core/api/admin.py` | 190 | `user.flags.ignore_permissions = True` |
| `construction_core/api/admin.py` | 214 | `customer.flags.ignore_permissions = True` |
| `construction_core/api/admin.py` | 231 | `contact.flags.ignore_permissions = True` |
| `construction_core/api/public.py` | 376 | `lead.flags.ignore_permissions = True` |
| `construction_core/change_orders.py` | 50 | `co.flags.ignore_permissions = True` |
| `construction_core/change_orders.py` | 69 | `co.save(ignore_permissions=True)` |
| `construction_core/change_orders.py` | 99 | `co.flags.ignore_permissions = True` |
| `construction_core/change_orders.py` | 117 | `co.save(ignore_permissions=True)` |
| `construction_core/change_orders.py` | 141 | `co.save(ignore_permissions=True)` |
| `construction_core/change_orders.py` | 150 | `co.flags.ignore_permissions = True` |
| `construction_core/change_orders.py` | 161 | `co.save(ignore_permissions=True)` |
| `construction_core/change_orders.py` | 178 | `m.flags.ignore_permissions = True` |
| `construction_core/change_orders.py` | 222 | `m.flags.ignore_permissions = True` |
| `construction_core/change_orders.py` | 260 | `si.flags.ignore_permissions = True` |
| `construction_core/construction_core/doctype/project_stage/project_stage.py` | 81 | `"Project Stage", filters={"project": project}, fields=["weight", "progress"], ignore_permissions=True` |
| `construction_core/construction_core/doctype/project_stage/project_stage.py` | 94 | `ignore_permissions=True,` |
| `construction_core/construction_core/doctype/project_stage/project_stage.py` | 98 | `milestone.flags.ignore_permissions = True` |
| `construction_core/construction_core/doctype/project_stage/project_stage.py` | 109 | `"Project Stage", filters={"project": project}, pluck="weight", ignore_permissions=True` |
| `construction_core/construction_core/doctype/stage_update/stage_update.py` | 26 | `stage.flags.ignore_permissions = True` |
| `construction_core/construction_core/doctype/subcontract_claim/subcontract_claim.py` | 92 | `pi.flags.ignore_permissions = True` |
| `construction_core/costing/engine.py` | 46 | `).insert(ignore_permissions=True)` |
| `construction_core/documents.py` | 216 | `f.flags.ignore_permissions = True` |
| `construction_core/documents.py` | 230 | `doc.flags.ignore_permissions = True` |
| `construction_core/documents.py` | 325 | `f.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 61 | `).insert(ignore_permissions=True)` |
| `construction_core/esign.py` | 148 | `f.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 204 | `req.insert(ignore_permissions=True)` |
| `construction_core/esign.py` | 208 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 263 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 316 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 344 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 385 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 402 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 410 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 447 | `req.save(ignore_permissions=True)` |
| `construction_core/esign.py` | 500 | `cust.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 527 | `project.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 547 | `stage.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 553 | `task.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 566 | `m.flags.ignore_permissions = True` |
| `construction_core/esign.py` | 613 | `req.save(ignore_permissions=True)` |
| `construction_core/media.py` | 74 | `copy.insert(ignore_permissions=True)` |
| `construction_core/media.py` | 81 | `frappe.delete_doc("File", name, ignore_permissions=True, force=True)` |
| `construction_core/money.py` | 30 | `).insert(ignore_permissions=True)` |
| `construction_core/money.py` | 47 | `).insert(ignore_permissions=True)` |
| `construction_core/money.py` | 78 | `.insert(ignore_permissions=True)` |
| `construction_core/money.py` | 96 | `template.insert(ignore_permissions=True)` |
| `construction_core/money.py` | 171 | `m.flags.ignore_permissions = True` |
| `construction_core/money.py` | 181 | `m.flags.ignore_permissions = True` |
| `construction_core/money.py` | 201 | `m.flags.ignore_permissions = True` |
| `construction_core/overrides/project.py` | 48 | `stage.flags.ignore_permissions = True` |
| `construction_core/payments/online.py` | 67 | `p.flags.ignore_permissions = True` |
| `construction_core/payments/online.py` | 205 | `pe.flags.ignore_permissions = True` |
| `construction_core/payments/online.py` | 386 | `pe.flags.ignore_permissions = True` |
| `construction_core/payments/reminders.py` | 109 | `log.insert(ignore_permissions=True)` |
| `construction_core/procurement.py` | 153 | `mr.flags.ignore_permissions = True` |
| `construction_core/push.py` | 100 | `frappe.delete_doc("Push Subscription", sub.name, ignore_permissions=True, force=True)` |
| `construction_core/push.py` | 202 | `.insert(ignore_permissions=True)` |
| `construction_core/push.py` | 213 | `frappe.delete_doc("Push Subscription", name, ignore_permissions=True, force=True)` |
| `construction_core/sales.py` | 47 | `).insert(ignore_permissions=True)` |
| `construction_core/sales.py` | 271 | `).insert(ignore_permissions=True)` |
| `construction_core/scheduling.py` | 73 | `doc.insert(ignore_permissions=True)` |
| `construction_core/scheduling.py` | 87 | `doc.save(ignore_permissions=True)` |
| `construction_core/selections.py` | 100 | `doc.save(ignore_permissions=True)` |
| `construction_core/selections.py` | 122 | `doc.save(ignore_permissions=True)` |
| `construction_core/selections.py` | 132 | `doc.save(ignore_permissions=True)` |
| `construction_core/selections.py` | 150 | `doc.save(ignore_permissions=True)` |
| `construction_core/selections.py` | 180 | `new.insert(ignore_permissions=True)` |
| `construction_core/selections.py` | 183 | `doc.save(ignore_permissions=True)` |
| `construction_core/selections.py` | 187 | `doc.save(ignore_permissions=True)` |
| `construction_core/setup/demo.py` | 67 | `).insert(ignore_permissions=True)` |
| `construction_core/setup/demo.py` | 82 | `).insert(ignore_permissions=True)` |
| `construction_core/setup/demo.py` | 99 | `).insert(ignore_permissions=True)` |
| `construction_core/setup/demo.py` | 125 | `doc.save(ignore_permissions=True)` |
| `construction_core/setup/demo.py` | 138 | `frappe.delete_doc("File", f, ignore_permissions=True, force=True)` |
| `construction_core/setup/demo.py` | 139 | `frappe.delete_doc("Design Template", DEMO_SLUG, ignore_permissions=True, force=True)` |
| `construction_core/setup/demo.py` | 141 | `frappe.delete_doc("Phase Template", DEMO_TEMPLATE, ignore_permissions=True, force=True)` |
| `construction_core/sitelog.py` | 139 | `doc.insert(ignore_permissions=True)` |
| `construction_core/sitelog.py` | 177 | `ignore_permissions=True` |
| `construction_core/sitelog.py` | 235 | `ts.insert(ignore_permissions=True)` |
| `construction_core/sitelog.py` | 308 | `doc.save(ignore_permissions=True)` |
| `construction_core/subcontracts.py` | 39 | `).insert(ignore_permissions=True)` |
| `construction_core/subcontracts.py` | 72 | `.insert(ignore_permissions=True)` |
| `construction_core/subcontracts.py` | 93 | `).insert(ignore_permissions=True)` |
| `construction_core/subcontracts.py` | 147 | `doc.flags.ignore_permissions = True` |
| `construction_core/subcontracts.py` | 199 | `je.flags.ignore_permissions = True` |
| `construction_core/subcontracts.py` | 274 | `pe.flags.ignore_permissions = True` |
| `construction_core/subcontracts.py` | 421 | `pi.flags.ignore_permissions = True` |
| `construction_core/sync.py` | 137 | `).insert(ignore_permissions=True)` |
