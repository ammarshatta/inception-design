# Phase 15 — Online payments and reminders

## Goal
Clients can pay a due milestone from the portal by card or mobile wallet. Paid amounts reconcile automatically into ERPNext. Overdue amounts get polite automatic reminders.

Projul equivalents: payment processing, and invoicing with automated reminders.

## Cost note (for the owner — approval required before going live)

An Egyptian gateway charges a fee per transaction. One public listing shows **Paymob at 2.75% per transaction**, with 1–3 business days settlement. Confirm the current rates and the merchant onboarding requirements directly with the provider.

Development uses the provider's **sandbox only**, which is free. Bank transfer and InstaPay stay available as manual methods, with no gateway fee.

## Design
- A provider-neutral interface, `construction_core/payments/gateway.py`, with `create_checkout`, `verify_webhook` and `refund`. The first adapter is Paymob (cards and Egyptian mobile wallets).
- A commercial ERPNext Paymob connector exists (from $999). Build our own adapter instead, unless the owner prefers to buy it.

## Tasks

1. **Pay from the portal:**
   - "ادفع دلوقتي" on a Due or Invoiced milestone.
   - The server creates an ERPNext `Payment Request` and a gateway checkout, then redirects the client.
2. **Webhook:**
   - A guest endpoint verifies the HMAC signature **before** reading anything.
   - It is idempotent on the gateway transaction ID.
   - It creates and submits a `Payment Entry` against the invoice; the milestone becomes Paid (phase 6 logic).
   - A scheduled job re-checks pending checkouts every 15 minutes, in case a webhook was missed.
3. **Manual methods:** the client uploads a bank transfer or InstaPay receipt. The accountant confirms it, which creates the Payment Entry.
4. **Receipts:** an Arabic PDF receipt is emailed and shown in the portal.
5. **Reminders:**
   - A daily scheduler sends milestone reminders: 3 days before due, on the due date, then 7 and 14 days overdue.
   - Templates are editable and in Arabic.
   - Channels: email and portal notification, plus a `wa.me` link list for the admin to send by hand.
   - ERPNext **Dunning** is used for formal overdue letters.
6. **Refunds:** a refund action is restricted to Accounts Manager. It calls the gateway and creates a reversing entry with an audit note.

## Acceptance criteria
- [ ] Sandbox end to end: pay a milestone, receive the webhook, the Payment Entry is submitted and the portal shows Paid.
- [ ] A webhook with a bad HMAC is rejected and logged. A duplicate webhook does not create a second Payment Entry (tests).
- [ ] The missed-webhook sweep reconciles a payment whose webhook was dropped (test with a mocked gateway).
- [ ] The reminder schedule sends exactly the expected messages over a simulated 30-day period (test with time freezing).
- [ ] No gateway secret is in git, and the live keys are never used locally.
