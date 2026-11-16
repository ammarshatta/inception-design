# Phase 6 — Money

## Goal
Milestone payments and site expenses are booked in ERPNext's own accounting, and the project's financial summary matches the General Ledger.

## Tasks

1. **Milestone → invoice:**
   - On a Due milestone, a "اعمل فاتورة" button creates a **draft** `Sales Invoice` with:
     - the customer and `project`
     - one service item, "دفعة: <label>"
     - the milestone amount
   - The accountant reviews and submits it. On submit, the milestone becomes Invoiced and stores `sales_invoice`.
2. **Collection:**
   - `Payment Entry.on_submit`: when the linked invoice is fully paid, the milestone becomes Paid.
   - `on_cancel`: it goes back to Invoiced.
3. **Expenses:**
   - `Purchase Invoice` with `project` and the custom `project_stage`.
   - Create the item groups: خامات, عمالة, معدات, نقل.
4. **VAT:**
   - A Sales Taxes and Charges Template for Egyptian VAT.
   - The rate is entered by the accountant and is never hardcoded.
5. **Script Report "ملخص مالي للمشروع"**, per project:
   - contract value (sum of milestones), invoiced, collected, and outstanding
   - actual expenses by item group and by stage
   - budget versus actual (`Project.estimated_costing`)
6. **Arabic Sales Invoice print format**, if phase 4 did not already finish it.

## Acceptance criteria
- [ ] Full cycle test: Due → draft invoice → submit → Payment Entry → milestone Paid → the portal shows Paid.
- [ ] Cancelling the Payment Entry returns the milestone to Invoiced (test).
- [ ] An automated test checks that the report totals for a sample project equal the General Ledger and Accounts Receivable to the piastre.
- [ ] `grep` shows no raw `float(` in our money code. List the matches in the report and justify any that remain.
- [ ] Submitted invoices cannot be edited. Corrections only go through cancel and amend.
