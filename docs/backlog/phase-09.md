# Phase 9 stories

## P09-01 · Finish selections · Must

**Role:** Office  
**Story:** As the office, I want a catalog of finish options with photos and prices, so that clients choose from what we can supply.

**Acceptance criteria**

1. Given a category with options linked to items, when I view an option, then it shows photos, brand, origin and the current price from the library.

## P09-02 · Finish selections · Must

**Role:** Engineer  
**Story:** As an engineer, I want to assign selections to a project with an allowance and a due date, so that choices are made on time and in budget.

**Acceptance criteria**

1. Given a project, when I add a selection for floor tiles in the reception, 40 m², allowance 20,000 EGP, due in 10 days, then the client sees it in اختياراتي.

## P09-03 · Finish selections · Must

**Role:** Client  
**Story:** As a client, I want to see the price effect of each option before choosing, so that I decide with full information.

**Acceptance criteria**

1. Given an allowance of 500 EGP/m² and an option at 650 EGP/m² for 40 m², when I view the option, then it shows + 6,000 EGP.
2. Given an option within the allowance, when I view it, then it shows ضمن الميزانية.

## P09-04 · Finish selections · Must

**Role:** Client  
**Story:** As a client, I want to approve my choices, so that the office can order materials.

**Acceptance criteria**

1. Given a choice over the allowance, when I approve, then I am asked to sign, and after signing a draft change order with the difference is created.
2. Given an approved selection, when I or the engineer try to change it, then it is locked.

## P09-05 · Finish selections · Should

**Role:** Procurement  
**Story:** As a procurement, I want a purchase list from approved selections, so that we order the right items on time.

**Acceptance criteria**

1. Given approved and unapproved selections, when I run the purchase list, then only approved ones show with item, quantity and date needed.

## P09-06 · Finish selections · Should

**Role:** Client  
**Story:** As a client, I want reminders before selection due dates, so that I do not delay the work.

**Acceptance criteria**

1. Given a selection due in 3 days, when the daily job runs, then I get a reminder; on the due date I get another.

## P09-07 · Finish selections · Could

**Role:** Admin  
**Story:** As an admin, I want to unlock a selection with a reason, so that mistakes can be corrected with a record.

**Acceptance criteria**

1. Given a locked selection, when I unlock it with a reason, then a new revision is created and the reason is logged.
