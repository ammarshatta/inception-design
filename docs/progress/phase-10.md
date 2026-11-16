# Phase 10 — Change orders

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

## What was done

| Task | Where |
|---|---|
| DocType Change Order (submittable). It reuses `Estimate Line` for pricing. The value is computed by the phase 7 engine, never typed, and removals are negative quantities. | `doctype/change_order/` |
| The client's "اطلب تعديل", or an engineer on site, creates a Draft with a description and photos; the engineer and admin are notified. The source is Client Request or Site Condition. | `change_orders.request_change`, `ClientChanges.vue` |
| Approval chain: engineer approves → admin sends to the client (PDF + signature, phase 8) → client signs (approved and submitted) or rejects with a reason. The status changes only through these actions. | `engineer_approve`, `send_to_client`, `on_signed`, `on_declined` |
| Effects: a positive value creates a Payment Milestone (Due on approval, or Upcoming when tied to a stage). The budget (`estimated_costing`) is increased by the cost subtotal. Schedule impact shifts that stage and the later ones, plus their tasks, and notifies the client. | `apply_effects`, `scheduling.shift_stages` |
| A negative value is either taken off the next unpaid milestone or turned into a draft credit note (Sales Invoice return), as the accountant chooses (`credit_mode`) | `apply_credit` |
| Portal: the client sees every change order with its status, amount and signed PDF | `project_change_orders`, `ClientChanges.vue` |
| A Change Order PDF in Arabic for signing | `print_format/inceptiondesign_change_order` |

## Decisions

1. **The budget grows by the cost subtotal** (before overhead and profit), because the budget is a cost figure. The milestone uses the full value the client pays.
2. **System follow-ups run as Administrator.** These are the kickoff, the effects of an approved change order, and the PDF rendering after a client action. The client's own action was already permission-checked. This is needed because ERPNext shares a project with its team when the project is saved, and a client has no share rights. See `utils.as_system`.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Full cycle: request → price → admin sends → client signs → milestone created, budget updated | `test_positive_cycle_creates_milestone_and_budget` (unit). The Playwright version is in `e2e/changes.spec.ts`. | ✅ CI |
| A negative change order makes a credit that Accounts Receivable shows correctly (10,000 − 2,000 = 8,000) | `test_negative_credit_note_in_receivables` | ✅ CI |
| An approved change order cannot be edited | `test_approved_cannot_be_edited` | ✅ CI |
| Schedule impact moves the stage and the later ones by the right number of days (Done stages stay) | `TestScheduleShift` | ✅ CI |
