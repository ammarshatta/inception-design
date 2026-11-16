# Phase 15 — Online payments and reminders

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate.

## Cost and accounts (owner decision before going live)

- Paymob charges per transaction (one public listing: 2.75% per transaction, settlement in 1–3 business days). Confirm the current rate with Paymob.
- Development and CI use **no gateway at all**: the gateway is mocked in tests. A real sandbox run needs a free Paymob test account **in the owner's name** (rule 14), so it is in "Owner checks at the end".
- Bank transfer and InstaPay need no gateway and have no fee.
- We built our own adapter (free) instead of the commercial ERPNext Paymob connector (from $999).

## What was built

| Task | Where |
|---|---|
| Provider-neutral interface: `create_checkout`, `verify_webhook`, `parse_webhook`, `inquire`, `refund` | `payments/gateway.py` |
| Paymob adapter: Intention API + Unified Checkout (cards, mobile wallets), HMAC-SHA512 over the 20 documented fields (unit-tested against Paymob's published example), transaction inquiry, refund | `payments/paymob.py` |
| Keys live in Settings as **Password** fields (encrypted in the site DB, never in git). **Live mode is refused on any test/dev/localhost site** | `Inceptiondesign Settings` → "الدفع أونلاين", `gateway.get_gateway` |
| "ادفع دلوقتي بالكارت" / "محفظة موبايل" on a Due or Invoiced milestone → Online Payment (Pending, own random reference) → redirect to Paymob | `payments/online.start_checkout`, `ClientPayments.vue` |
| Webhook (the only guest endpoint, in `api/public.py`): HMAC checked **before** anything is read; bad/missing signature → 401 + Error Log entry (no card data); idempotent on the gateway transaction ID with a row lock | `api/public.paymob_webhook`, `online.reconcile`, `online.book` |
| Booking: the milestone's invoice (made and submitted if the milestone was only Due), then a submitted Payment Entry to the gateway clearing account; phase 6 marks the milestone Paid | `online.book` |
| Missed webhooks: every 15 minutes pending checkouts are checked with the gateway; expired after 3 days | `online.sweep_pending` (cron in `hooks.py`) |
| After the redirect back, the portal checks the status once | `online.payment_status` |
| Bank transfer / InstaPay: the client uploads the receipt photo; accountants get a notification; confirm → Payment Entry to the "manual" account; reject → client notified | `online.submit_transfer`, `confirm_transfer`, `reject_transfer` |
| Arabic receipt PDF (print format "Inceptiondesign Receipt"), emailed when an outgoing email account exists, downloadable in the portal | `online.send_receipt`, `receipt_pdf` |
| Reminders: day −3, 0, +7, +14 around the due date, once each; editable Arabic templates in Settings; portal notification + email (if set up) + a wa.me link per reminder for the admin | `payments/reminders.py`, `Payment Reminder Log`, `todays_whatsapp` |
| Refund: Accounts Manager only; gateway refund, then the Payment Entry is cancelled (ERPNext posts the reversing ledger entries), note kept on both records | `online.refund` |
| Formal overdue letters: ERPNext **Dunning** on the Sales Invoice (built in, nothing added) | — |

## Not done

- A desk button for accountants to confirm/reject transfers: they use the API methods from the Online Payment list for now (fields are read-only on purpose). A small form script is the next step.
- Partial online payments: the client pays the full outstanding of a milestone.

## Decisions to review

1. The plan mentions an ERPNext `Payment Request`. We record the checkout in our own **Online Payment** record and book a normal Payment Entry. A Payment Request needs a Payment Gateway Account set-up per company and adds nothing here; the ledger result is the same.
2. A refund cancels the original Payment Entry instead of adding a second entry; ERPNext v16 posts reversing GL rows on cancel, and the invoice is open again.
3. Paying a milestone that is only "Due" makes and submits its invoice automatically at the moment the payment is confirmed.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Pay a milestone, webhook received, Payment Entry submitted, portal shows Paid | `test_payments.test_pay_due_milestone_by_webhook_once` (gateway mocked) | ✅ CI |
| Sandbox end to end with the real Paymob test environment | needs the owner's Paymob test account | ☐ (owner) |
| Bad HMAC rejected and logged; duplicate webhook → one Payment Entry | `test_bad_signature_rejected_and_logged`, `test_pay_due_milestone_by_webhook_once` | ✅ CI |
| Missed-webhook sweep reconciles (mocked gateway) | `test_sweep_reconciles_missed_webhook` | ✅ CI |
| Reminders over a simulated 30 days: days 7, 10, 17, 24 only | `test_thirty_days_exactly_four_reminders` | ✅ CI |
| Transfer receipt → accountant notified → confirm creates the Payment Entry | `test_manual_transfer_confirmed_by_accountant` | ✅ CI |
| Receipt PDF in the portal | same webhook test (`receipt_pdf`) | ✅ CI |
| Refund only by Accounts Manager, gateway refund + reversal with note | `test_refund_only_accounts_manager` | ✅ CI |
| No gateway secret in git; live keys never used locally | Password fields; `test_live_keys_refused_on_test_site` | ✅ CI |
