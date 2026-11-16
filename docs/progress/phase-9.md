# Phase 9 — Finish selections

**Status:** 🔵 Code written on 17 Nov 2026; waiting for CI.

## What was done

| Task | Where |
|---|---|
| DocTypes: Selection Category, Selection Option (photos, brand, origin, item or unit price), Project Selection (allowance, qty, due date, status Open → Chosen → Awaiting Signature → Locked) | `doctype/` |
| An option's price comes from the price library when it is linked to an item, otherwise from its unit price. The price is captured when the client chooses. | `selections.option_price` |
| Client "اختياراتي" (`/portal/c/<project>/selections`): one card per selection, with option photos and a live difference: "ضمن الميزانية" or "+ X ج.م" | `ClientSelections.vue`, `selections.project_selections` |
| Approval: within the allowance it is locked right away. Over the allowance the client signs (phase 8), then it is locked and a draft Change Order with the difference is created. | `selections.approve`, `on_signed`, `change_orders.draft_from_selection` |
| Locked: neither the client nor the engineer can change it. People cannot change the choice fields at all; they change only through the portal actions. | `project_selection.py` |
| Purchase list report (`Purchase List`): approved or locked selections only, with item, quantity and date needed (stage start, else due date) | `report/purchase_list/` |
| Reminders: a daily job notifies the client 3 days before the due date and on the day. Overdue selections show on the engineer's project page. | `selections.send_reminders`, `ProjectPage.vue` |
| Admin unlock with a logged reason. A signed selection gets a new revision; the old one is marked Superseded and never edited. | `selections.unlock` |

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Price difference with the allowance above, equal to and below the price | `test_selections_changes.TestPriceDifference` | pending CI |
| The client chooses over the allowance, signs, and a draft Change Order with the right amount exists | `test_over_allowance_sign_creates_draft_change_order` (Playwright for this flow is added with phase 10's cycle) | pending CI |
| A locked selection cannot be changed by the client or the engineer | `test_locked_cannot_change` | pending CI |
| The purchase list shows only approved selections, with the right quantities | `test_purchase_list_only_approved` | pending CI |
