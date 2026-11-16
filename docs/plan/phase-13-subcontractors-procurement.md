# Phase 13 — Subcontractors and procurement

## Goal
Materials are bought against approved needs with purchase orders. Subcontractors work under recorded agreements and are paid against approved progress claims (مستخلصات), with retention. All costs land on the right project and stage.

Projul equivalents: purchase orders, subcontractor management, and job costing.

## Reuse from ERPNext
- **`Supplier`**, with a Supplier Group of "مقاولين باطن" or "موردين خامات".
- **`Material Request`, `Request for Quotation`, `Supplier Quotation` and `Purchase Order`.**
- **`Purchase Receipt`, `Purchase Invoice` and `Payment Entry`.**

Optional: the ERPNext **Supplier Portal**, so subcontractors can see their orders and invoices.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Subcontract` | normal (submittable) | supplier, project, scope, lines (table: `Subcontract Line`: description, qty, uom, rate, project_stage), contract_value, retention_pct, advance_amount, start/end dates, signature_request (phase 8), status |
| `Subcontract Claim` | normal (submittable) | subcontract, claim_no, period_to, lines (table: `Subcontract Claim Line`: subcontract_line, previous_qty, current_qty, cumulative_qty, amount), gross, retention_amount, advance_recovery, net_due, approved_by, purchase_invoice |

## Tasks

1. **From needs to orders:**
   - Approved selections (phase 9) and estimate material lines (phase 7) can generate a `Material Request` per project and stage, with the needed-by date.
   - Material Request → RFQ to 2–3 suppliers → Supplier Quotation comparison report → Purchase Order.
   - Each PO line carries `project` and `project_stage` (custom field).
2. **Receiving:**
   - A `Purchase Receipt` on site; the engineer confirms from the portal with a photo of the delivery note.
   - The Purchase Invoice follows.
3. **Subcontracts:** recorded and signed through phase 8, with retention % and an advance.
4. **Progress claims (مستخلصات):**
   - Previous quantities are pulled in automatically.
   - Cumulative quantity can never exceed contract quantity without an Admin override, which is logged.
   - Net due = gross − retention − advance recovery.
   - Approval creates a `Purchase Invoice` with the retention booked to a "Retention Payable" account.
5. **Retention release:** at the end of the project, an action releases the retention with a Payment Entry.
6. **Reports:**
   - Supplier quotation comparison.
   - Subcontract status: value, claimed, paid, retention held.
   - Committed cost (open POs and subcontracts) per project.

## Acceptance criteria
- [ ] Claim math tests: 3 consecutive claims, with retention and advance recovery, matching a hand calculation.
- [ ] An over-quantity claim is blocked without the Admin override (test).
- [ ] PO and invoice costs appear under the right project and stage in the phase 6 financial report (test).
- [ ] Playwright: Material Request → PO → Receipt → Invoice for one project.
- [ ] Retention payable in the General Ledger equals the sum of retention on approved claims (test).
