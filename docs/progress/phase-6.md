# Phase 6 — Money

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

## What was done

| Task | Where |
|---|---|
| "اعمل فاتورة" on a Due milestone: a **draft** Sales Invoice with the customer, the project, one service item "دفعة تعاقد" described as "دفعة: <label>", and the milestone amount. A second click opens the same draft. | `money.make_invoice`, `public/js/payment_milestone.js`, custom field `Sales Invoice.payment_milestone` |
| Submitting the invoice sets the milestone to Invoiced and links it (or Paid, if it is already settled). Cancelling sets it back to Due. | `money.sales_invoice_on_submit/on_cancel` |
| Payment Entry: a fully paid invoice sets its milestone to Paid. Cancelling the payment sets it back to Invoiced. Partial payments keep it Invoiced. | `money.payment_entry_on_submit/on_cancel` |
| Expenses: Purchase Invoice with `project` and `project_stage`; item groups خامات / عمالة / معدات / نقل (plus "دفعات العملاء" for the service item) | `money.ensure_item_groups` |
| VAT: a "ضريبة القيمة المضافة" Sales Taxes template and Tax account per company, created with rate **0**. The accountant enters the rate. ERPNext's own "Egypt Tax" template at 10% from the setup wizard is left untouched; use ours. | `money.ensure_vat_template` (after migrate and on new companies) |
| Script report "ملخص مالي للمشروع" (`Project Financial Summary`): contract value, invoiced, collected, outstanding, expenses by type and by stage, budget vs actual, plus a bar chart | `report/project_financial_summary/` |
| Arabic invoice print format | Done in phase 4 |

## Decisions

1. **"Invoiced" uses the grand total, after VAT.** That is what the client owes and what the General Ledger shows. **Expenses use the net amount, before input VAT**, because that is the project's real cost.
2. **The report has an English internal name** (`Project Financial Summary`) and the Arabic title is on the workspace shortcut. An Arabic report name becomes a Python module path, which is fragile.

## `float(` check

`grep -rn "float(" construction_core frontend/src` (excluding tests) finds **no matches**. Money uses `flt(value, 2)` everywhere.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Full cycle: Due → draft → submit → Payment Entry → Paid → the portal shows Paid | `test_money.test_full_cycle_and_cancel` | ✅ CI |
| Cancelling the Payment Entry returns the milestone to Invoiced | same test | ✅ CI |
| Report totals equal the GL and Accounts Receivable to the piastre (amounts with piastres: 85000.55, 40000.25, 10000.10, 1500.5, 3200.25) | `test_report_matches_general_ledger` | ✅ CI |
| No raw `float(` in money code | grep above | ✅ |
| A submitted invoice cannot be edited | `test_submitted_invoice_cannot_be_edited` | ✅ CI |
| P06-04: VAT at the rate the accountant entered | `test_vat_template_rate_from_accountant` | ✅ CI |
