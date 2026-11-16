# Phase 9 — Finish selections

## Goal
The client chooses finishes (tiles, paint, sanitary ware, doors, lighting…) in the portal, sees the price effect of each choice against the contract allowance, and approves. The choices feed procurement and, when they cost more, a change order.

Projul equivalent: Selections. This matters most for a finishing company.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Selection Category` | normal | category_name (e.g. سيراميك أرضيات), default_uom, sort_order |
| `Selection Option` | normal | category, option_name, item (link to Item), brand, origin, unit_price (from the price library), images (table), active |
| `Project Selection` | normal | project, project_stage, category, room_or_area, qty, uom, allowance_amount (included in the contract), due_date, status (Open / Chosen / Approved / Locked), chosen_option, price_difference (read only), signature_request, notes |
| `Selection Option Image` | child | file, caption |

## Tasks

1. **Office setup:**
   - Manage categories and options with photos.
   - An option's price comes from the price library (phase 7), captured when the client chooses.
2. **Selections on a project:**
   - Create from a list per stage, or copy from the design template.
   - Set an allowance for each.
   - Set a due date, for example before the stage starts.
3. **Client portal "اختياراتي":**
   - A card per selection, with photos of the options.
   - The difference is shown live: (option price − allowance ÷ qty) × qty.
     - "ضمن الميزانية" in green, or "+ X جنيه".
   - The client chooses, then approves.
   - Approval of anything **over** the allowance requires signing (phase 8).
   - An approved selection is Locked.
4. **Effects of approval:**
   - The difference creates a draft **Change Order** (phase 10). If the difference is zero or negative, it is only recorded.
   - Approved selections appear in a "قائمة الشراء" report per project (item, qty, date needed), used by procurement in phase 13.
5. **Reminders:**
   - Notify the client 3 days before a due date and on the day.
   - Show overdue selections on the engineer's project page.
6. **Admin override:**
   - The admin can unlock a selection, with a reason that is logged.
   - Unlocking a signed selection creates a new revision; it never edits the old one.

## Acceptance criteria
- [ ] Unit test for the price difference, with allowance above, equal to and below the option price.
- [ ] Playwright: the client chooses an over-allowance option, signs, and a draft Change Order with the right amount exists.
- [ ] A Locked selection cannot be changed by the client or the engineer (test).
- [ ] The purchase list report shows only approved selections, with correct quantities.
