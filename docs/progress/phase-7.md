# Phase 7 — Sales pipeline and estimating

**Status:** 🟢 Unit tests green in CI (run 43975747126, 17 Nov 2026). Playwright results are recorded in PROGRESS.md as they come in.

## What was done

| Task | Where |
|---|---|
| Pipeline: custom field `Opportunity.pipeline_stage` (جديد → معاينة → تسعير → عرض مرسل → تفاوض → اتكسب / اتخسر), Kanban board "مسار المبيعات", and track changes on Opportunity, so every drag is logged. Lead → Opportunity uses ERPNext's own "Create Opportunity", and a new opportunity starts at جديد. | fixtures, `sales.ensure_sales_setup` |
| Follow-ups: an ERPNext ToDo with a due date (`sales.add_followup`) | `sales.py` |
| Price library: `Item Price` on the buying price list "أسعار الخامات" with `valid_from`, `price_source` and `source_ref`; `Labor Rate` (by governorate, dated). Prices cannot be deleted: add a newer price instead. | `costing/engine.py`, `sales.py`, fixtures |
| Bulk import (CSV or XLSX) with a downloadable template and an error per row | `sales.import_prices`, `sales.price_import_template` |
| Costing engine using `Decimal` only. Assembly unit cost = Σ(qty × (1 + waste) × price). Lines are split into Material, Labor, Equipment and Other. Overhead, then profit, then VAT from the template. Rounding happens only on each line total and on the final total. | `costing/engine.py` |
| DocTypes: Labor Rate, Assembly (+ line), Estimate (submittable, + line). While an estimate is a draft, prices are looked up for its date and captured into each line. Once approved (submitted), it never changes. | `doctype/` |
| Revisions: "مراجعة جديدة" creates revision N+1 and marks the old one Superseded. `compare_revisions` lists lines added, removed and changed, with the money difference. "ابدأ من تصميم" makes each design stage a section. Duplicate uses Frappe's own duplicate. | `sales.py`, `public/js/estimate.js` |
| Estimate → Quotation: one line per section. Each section's share of (subtotal + overhead + profit) is computed so the lines add up exactly; VAT comes from the same template; the Quotation links back to the estimate. | `sales.make_quotation`, custom field `Quotation.estimate` |
| New role **Construction Sales** (desk): leads, opportunities, quotations, prices and estimates, with no accounting | fixtures, `setup/install.py` |

## `float(` check

`grep -rn "float(" construction_core/costing` finds **no matches**.

## Decisions

1. **Line type "Other"** has a unit cost that is typed in rather than looked up (for one-off items, and for the placeholder lines created from a design).
2. **Price deletion** is blocked only for the buying price list "أسعار الخامات" and for Labor Rate. Other ERPNext price lists keep their normal behaviour.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Engine: known totals with waste, overhead, profit and VAT, to the piastre (2235.26; 5840.51) | `test_estimating.TestEngine`, `test_estimate_total_with_vat` | ✅ CI |
| A new Item Price after approval does not change the estimate | `test_approved_estimate_keeps_captured_price` | ✅ CI |
| `compare_revisions` with an added, a removed and a changed line | `test_revise_and_compare` | ✅ CI |
| Lead → Opportunity → Estimate → Quotation end to end in Playwright | `e2e/sales.spec.ts`. It drives the server API and then opens the Kanban and the Quotation in the desk. | pending CI |
| No `float(` in `costing/` | grep above | ✅ |
| P07-02: the January price is used for a February estimate; prices cannot be deleted | `test_price_in_force_on_date`, `test_prices_cannot_be_deleted` | ✅ CI |
| P07-03: assembly for 50 m² | `test_assembly_for_50_m2` | ✅ CI |
| P07-07: import with per-row errors | `test_import_prices_with_row_errors` | ✅ CI |
