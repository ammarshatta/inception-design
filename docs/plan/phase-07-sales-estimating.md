# Phase 7 — Sales pipeline and estimating

## Goal
Every lead moves through a visible pipeline. The office builds an accurate estimate from reusable assemblies and dated prices, and turns it into an ERPNext Quotation.

Projul equivalents: CRM and lead pipeline, estimating with templates and assemblies, and job budgets.

## Reuse from ERPNext
- **`Lead`, `Opportunity` and `Quotation`** for the sales stages.
- **`Item`, `Item Group` and `UOM`** for materials and units.
- **`Item Price`** on a **Buying** price list, with `valid_from`, for material prices.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Labor Rate` | normal | labor_type, uom, rate (Currency), governorate, valid_from, source |
| `Assembly` | normal | assembly_name (e.g. "متر سيراميك أرضيات شامل"), uom, items (table: `Assembly Line`), notes |
| `Assembly Line` | child | line_type (Material / Labor / Equipment / Other), item or labor_type, qty_per_unit, waste_pct |
| `Estimate` | normal (submittable) | customer or lead, opportunity, project (optional), design_template, revision, status (Draft / Approved / Superseded), overhead_pct, profit_pct, taxes_template, lines (table: `Estimate Line`), totals (read only) |
| `Estimate Line` | child | section (e.g. "الريسبشن"), description, assembly or item or labor_type, qty, uom, unit_cost (captured), waste_pct, line_total |

Custom field on `Item Price`: `price_source` (Quotation / Invoice / Market survey) and `source_ref`.

## Tasks

1. **Pipeline:**
   - A Kanban view of `Opportunity` by sales stage. Stages are configurable; defaults: جديد, معاينة, تسعير, عرض مرسل, تفاوض, اتكسب, اتخسر.
   - The public request form (phase 5) creates a Lead.
   - A "حوّل لفرصة" action creates the Opportunity.
   - Follow-up reminders use ERPNext `ToDo` with a due date.
2. **Price library:**
   - Material prices go in `Item Price` with `valid_from` and `price_source`. Old prices are never deleted.
   - Labor prices go in `Labor Rate`.
   - An import template (CSV or Excel) loads both in bulk.
3. **Costing engine** in `construction_core/costing/engine.py`, using `Decimal` only:
   - For each line, the unit cost comes from the price in force on the estimate date. It is **captured** into the line and never looked up again after approval.
   - Assembly unit cost = Σ(qty_per_unit × (1 + waste) × price).
   - Subtotal = Σ line totals, split by Material, Labor, Equipment and Other.
   - Then add overhead %, then profit %, then taxes from the template.
   - Rounding to 2 decimals happens only at the line-total level and at the final total.
4. **Estimate screen** (desk form):
   - Sections, lines and a live total.
   - Duplicate an estimate.
   - Start from a `Design Template`: the stages become sections.
5. **Revisions:**
   - Approving makes the estimate immutable.
   - "Revise" creates revision N+1 and marks the old one Superseded.
   - `compare_revisions(a, b)` shows added, removed and changed lines with the money difference.
6. **To Quotation:** an approved Estimate creates an ERPNext `Quotation` with one line per section and links back to it.

## Acceptance criteria
- [ ] Engine unit tests with fixed inputs give known totals, including waste, overhead, profit and VAT, to the piastre.
- [ ] Changing an `Item Price` after an estimate is approved does not change that estimate (test).
- [ ] `compare_revisions` output is correct for a test with an added line, a removed line and a changed line.
- [ ] Lead → Opportunity → Estimate → Quotation runs end to end in a Playwright test.
- [ ] No `float(` in `costing/` (grep in the report).
