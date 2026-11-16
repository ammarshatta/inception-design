# Phase 10 — Change orders

## Goal
Any change in scope, whether the client asks for it, the office proposes it, or a selection causes it, is priced by the engine, approved and signed by the client, and updates the budget, the schedule and the payments.

Projul equivalent: change orders, including from the field.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Change Order` | normal (submittable) | project, source (Client Request / Office / Selection / Site Condition), title, description, lines (table: `Estimate Line`, reused), cost_difference (read only), schedule_impact_days, status (Draft / Engineer Approved / Sent to Client / Approved / Rejected / Cancelled), signature_request, payment_milestone, photos |

## Tasks

1. **Client request from the portal:**
   - "اطلب تعديل" takes a description and photos and creates a Draft.
   - The engineer and admin are notified.
2. **Field creation:** the engineer can create a Draft from the portal on a phone, with photos. Pricing is done later in the desk.
3. **Pricing:** lines are priced with the phase 7 engine. Removals are negative lines. The cost difference is computed, never typed.
4. **Approval chain:**
   - The engineer approves → the admin sends to the client → the client signs (phase 8) or rejects with a reason.
   - Rejected and Cancelled orders keep their history.
5. **Effects on approval:**
   - **Positive difference:** create a new `Payment Milestone` linked to the change order. Its due rule is "on approval" or tied to a stage.
   - **Negative difference:** create a credit, as a Sales Invoice return or a reduction of the next milestone, as the accountant chooses.
   - **Budget:** add the difference to `Project.estimated_costing`.
   - **Schedule:** when `schedule_impact_days > 0`, shift the dependent stages and tasks (uses phase 11 logic) and notify the client.
6. **Portal:** the client sees all change orders with status, amount and the signed PDF.

## Acceptance criteria
- [ ] A full cycle in Playwright: the client requests, the engineer prices, the admin sends, the client signs, the milestone is created and the budget is updated.
- [ ] A negative change order produces a credit that the AR report shows correctly.
- [ ] An approved change order cannot be edited. Corrections are a new change order (test).
- [ ] Schedule impact moves the dependent stage dates by the right number of days (test, once phase 11 exists; until then, a stub test of the date function).
