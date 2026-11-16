# Phase 8 — Proposals, e-signature and kickoff

**Status:** 🟢 Unit tests green in CI (run 43975747126, 17 Nov 2026). Playwright results are recorded in PROGRESS.md as they come in.

> **Legal (for the owner):** this is a *simple electronic signature with a strong audit trail*, not an ITIDA-licensed signature under Egyptian Law 15/2004.
> - Ask a lawyer whether it is enough for your contracts.
> - `esign.PROVIDER_HOOK` marks where a licensed provider can be plugged in later.

## What was done

| Task | Where |
|---|---|
| DocTypes: Contract Template (Jinja body), Signature Request (+ Signature Event log), and Estimate Payment Term (payment terms on the estimate) | `doctype/` |
| A default Arabic contract template. The contract print format for Estimate renders the template with sections, totals, payment terms and the terms from Settings. A signature page print format. Both use PlutoPrint and RTL. | `esign.DEFAULT_BODY`, `print_format/inceptiondesign_contract`, `…_signature_page` |
| "ابعت للتوقيع" (`send_for_signature`): the PDF is rendered and stored **private** with its SHA-256; the client is notified in the portal and by email; a wa.me link is returned. `create_client` makes a portal client who has no project yet. | `esign.py`, `api/admin.create_client` |
| Signing in the portal (`/portal/sign/<name>`): read the PDF, request a 6-digit code by email (10 minutes, stored as an HMAC, 3 attempts), draw the signature (own canvas pad, no new dependency), confirm. Every step is logged with IP and user agent. | `SignPage.vue`, `SignaturePad.vue`, `esign.request_otp/sign` |
| Freezing: the signed PDF = original pages + signature page (name, signature, time, IP, original hash), merged with pypdf, and its hash is recorded. A Signed request can't be changed or deleted, and its files can't be deleted. `verify()` re-hashes both files. | `esign.build_signed_pdf`, `signature_request.py`, `overrides/file.on_trash` |
| Kickoff when an estimate is signed: Project (customer from the lead if needed), one stage per section with weights from each section's cost share (adding up to 100), one ERPNext Task per stage, one milestone per payment term (the first is Due), the client and the default engineer added to the team | `esign.kickoff` |
| Decline with a reason (the office is notified). The daily job expires old requests. A locked request is reopened with `resend`. | `esign.decline`, `expire_requests` (scheduler), `resend` |
| Clients see only the requests addressed to them | `permissions.signature_request_*` |

## Decisions

1. **The PDF is shown with the browser's built-in viewer (iframe), not pdf.js.** pdf.js would add a large dependency. Some phones open the PDF in a new tab instead, so there is a link for that.
2. **The OTP is sent by email only.** Clients without email (username accounts) can't sign yet. A WhatsApp or SMS code needs a paid provider, so it is listed as an owner decision.
3. **Test hook:** on test sites only (`allow_tests` + `cc_test_otp`), the last code is kept in the cache so Playwright can read it. Production never has these flags.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Playwright: the client opens the request, gets the code, signs, and the project appears | `e2e/sign.spec.ts` | pending CI |
| After signing, every change to the request or its files is rejected | `test_esign.test_signed_is_frozen_and_tamper_detected` | ✅ CI |
| The SHA-256 of the original matches `pdf_sha256`, and tampering is detected by `verify` | same test, plus `test_full_signing_and_kickoff` | ✅ CI |
| The 4th try after 3 wrong codes is locked until the office resends | `test_fourth_wrong_code_locks_until_resend` | ✅ CI |
| The signed PDF in Arabic RTL with the signature page (screenshot) | CI turns the signed PDF into PNGs (`53-signed-pdf-*.png`) | pending CI |
| P08-04: project, weighted stages, tasks, milestones, and the client on the team | `test_full_signing_and_kickoff` | ✅ CI |
| P08-05 / P08-06: decline with a reason; expiry | `test_decline_and_expiry` | ✅ CI |
