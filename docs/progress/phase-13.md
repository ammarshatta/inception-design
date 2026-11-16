# Phase 13 — Subcontractors and procurement

**Status:** 🔵 Code written on 17 Nov 2026; waiting for CI.

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate.

## Reused from ERPNext (rule 4: check before building)

| Need | ERPNext feature used as-is |
|---|---|
| RFQ to 2–3 suppliers | `Request for Quotation` (made from the Material Request with ERPNext's own button) |
| Price comparison | ERPNext's **Supplier Quotation Comparison** report |
| PO from the chosen quotation | ERPNext's "Create → Purchase Order" on the Supplier Quotation |
| Receipt and invoice | `Purchase Receipt`, `Purchase Invoice`, `Payment Entry` |

`project` and the new `project_stage` field sit on every item table (Material Request, RFQ, Supplier Quotation, Purchase Order, Purchase Receipt, Purchase Invoice). ERPNext's mappers copy same-named fields, so the stage follows the document chain.

## What was built

| Task | Where |
|---|---|
| Needs → Material Requests: material lines of approved estimates (assemblies expanded, waste included) and approved finish selections; one draft MR per stage; needed-by = stage start − 2 days (or today + 7); every need is requested once (`cc_source` on the MR item) | `procurement.make_material_requests`, `project_needs` |
| Engineer confirms a delivery on site with a photo of the delivery note: a submitted Purchase Receipt for the open quantities, the photo stored private, ≤ 1600 px, no EXIF; access is checked against the PO's project | `procurement.open_deliveries`, `confirm_delivery`; portal page `/portal/projects/<p>/deliveries` |
| Subcontract (submittable): lines with stage, contract value, retention %, advance. It becomes **Active only when the subcontractor signs it** (phase 8 e-signature, new print format "Inceptiondesign Subcontract"); after that it cannot be edited | `doctype/subcontract`, `subcontracts.send_for_signature`, `on_signed`, `esign.py` |
| New role **Construction Subcontractor** (portal only): signs their own subcontracts and sees nothing else | `fixtures/role.json`, `permissions.is_external_signer` |
| Progress claims (مستخلصات): previous quantities pulled automatically; cumulative above contract quantity is blocked unless the admin ticks the override (logged as a comment); engineer prepares, admin approves | `doctype/subcontract_claim`, `subcontracts.compute_claim` |
| Claim math (Decimal): gross − retention − advance recovery (advance × gross ÷ contract value; the claim that completes the contract recovers the remainder) | `subcontracts.compute_claim` |
| Approval books a submitted Purchase Invoice: expense = gross, per stage; retention to **محتجزات مقاولين الباطن** (liability); advance recovery to **سلف مقاولين الباطن** (asset) | `subcontracts.make_claim_invoice` |
| Advance payment: journal entry Dr سلف / Cr cash | `subcontracts.pay_advance` |
| Retention release: journal entry Dr محتجزات / Cr supplier, then a Payment Entry to the supplier | `subcontracts.release_retention` |
| Reports: **Committed Cost** (open PO rows not yet billed + unclaimed subcontract lines, per project and stage) and **Subcontract Status** (value, claimed, retention, advance recovered, paid) | `report/committed_cost`, `report/subcontract_status` |
| Project Financial Summary now takes the stage from the invoice **item** when set (claims and PO-based invoices span stages) | `report/project_financial_summary` |
| Foremen are now project-scoped (they reach projects their crew is assigned to) — this closes a gap from phases 11–12 where a foreman was not limited | `permissions.py` |

## Not done

- ERPNext Supplier Portal for subcontractors (optional in the plan).
- A desk button "اعمل طلبات الخامات" on the Project form: the method exists and is tested; it is called from the API for now.
- Retention release is all-at-once per subcontract (no partial release).

## Decisions to review

1. Material items are **non-stock** (as in phase 6–7), so receipts move no stock and post no GL; the cost is booked on the invoice.
2. The advance is booked to an asset account, not as an unallocated supplier advance, so the recovery on each claim is a plain deduction line.
3. A claim invoice is submitted automatically on approval (the accountant does not re-check it).

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| P13-01: approved selections and estimate lines → MRs per project and stage with needed-by dates | `test_procurement.test_1_material_requests_per_stage_once` | pending CI |
| P13-02: RFQ to 3 suppliers, comparison side by side, PO from the chosen one | `test_2_rfq_comparison_po_receipt_invoice` (ERPNext comparison report) | pending CI |
| P13-03: submitted PO with project and stage in committed cost | same test + `test_over_quantity_needs_admin_override` (subcontract part) | pending CI |
| P13-04: delivery confirmed on site with a photo → Purchase Receipt with the photo | same test; `e2e/procurement.spec.ts` | pending CI |
| P13-05: signed subcontract becomes active and cannot be edited | `test_signing_activates_and_freezes` | pending CI |
| P13-06 AC1: 3 claims with retention and advance recovery match the hand calculation; PI created | `test_three_claims_retention_advance_and_release` (15,400 / 23,800 / 30,800) | pending CI |
| P13-06 AC2: over-quantity blocked without admin override | `test_over_quantity_needs_admin_override` | pending CI |
| P13-07: retention release → payment, retention payable = 0 | `test_three_claims_retention_advance_and_release` | pending CI |
| Plan: PO and invoice costs under the right project and stage in the phase 6 report | unit test + e2e | pending CI |
| Plan: Playwright MR → PO → Receipt → Invoice | `e2e/procurement.spec.ts` | pending CI |
| Plan: retention payable in the GL = sum of retention on approved claims | unit test (10,000) | pending CI |
