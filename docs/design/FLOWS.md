# User flows (draft for engineer review)

**Status:** draft v1, 16 Nov 2026. These flows will change after the engineers give feedback.

Who does each step: **[Office]** office staff · **[Client]** the client · **[System]** automatic.

## Flow 1 · From website visitor to signed project (phases 5, 7, 8)
1. [Client] Visitor requests a design from the website.
2. [Office] The lead appears in the sales pipeline.
3. [Office] Site visit and measurements.
4. [Office] Estimate built from the price library.
5. [Client] Client signs the proposal in the portal.
6. [System] Project, stages and payments are created.

> Question: Who does the site visit and measurements today? What must the estimate show the client?

## Flow 2 · Adding a client and first login (phase 2)
1. [Office] Admin adds the client to the project.
2. Does the client have an email?
   - Yes: [System] a welcome email lets them set a password.
   - No: [Office] a username and a temporary password are sent on WhatsApp.
3. [Client] Client logs in with a password, Google or Facebook.
4. [System] A temporary password must be changed.
5. [Client] Client sees the portal home.

> Question: Do most clients have email? Would they use Google or Facebook login?

## Flow 3 · A day on site (phases 3, 12, 16)
1. [Office] Foreman clocks the crew in (GPS).
2. [Office] Engineer posts an update with photos.
3. [Office] Engineer ticks checklist items.
4. [System] No signal? The update is saved and synced later.
5. [System] Progress is recalculated from stage weights.
6. [Client] Client is notified of the update.

> Question: Do foremen have smartphones? Clock in per crew or per worker? Is the daily log enough?

## Flow 4 · Finish selections (phases 9, 10, 13)
1. [Office] Engineer sets a selection with an allowance and a due date.
2. [Client] Client picks an option and sees the price difference.
3. Is it over the allowance?
   - Yes: [Client] the client signs the extra cost, then [System] a change order is priced and a new payment is added.
   - No: [System] the choice is approved and locked, then added to the purchase list.
4. [Office] Procurement orders the materials.

> Question: Which items need client selections? Is the allowance per m² or per room?

## Flow 5 · From finished stage to payment (phases 6, 15)
1. [Office] Engineer marks the stage Done.
2. [System] Its payment becomes Due.
3. [Office] Accountant issues the invoice.
4. [Client] Client pays online or uploads a transfer receipt.
5. [System] The payment is recorded and the stage payment becomes Paid.
6. [System] Overdue? Reminders are sent.

> Question: Are payments tied to stages or to dates? Is it acceptable to pass card fees on to the client?

## Flow 6 · Client asks for a change (phase 10)
1. [Client] Client requests a change with photos.
2. [Office] Engineer prices it with the costing engine.
3. [Office] Admin sends it for signature.
4. [Client] Client signs or rejects.
5. [System] Budget, schedule and payments are updated.

> Question: Who reviews the price before the client sees it? How are delays usually agreed?

## Flow 7 · Subcontractor progress claim (phase 13)
1. [Office] Subcontract signed with a retention %.
2. [Office] Work is recorded in daily logs.
3. [Office] Engineer enters the claim; previous quantities are filled in.
4. [System] Over the contract quantity? Blocked unless an admin allows it.
5. [System] Approved: invoice minus retention.
6. [Office] Retention is released at handover.

> Question: Usual retention %? Are claims monthly or by stage? Who approves them?
