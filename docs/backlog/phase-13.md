# Phase 13 stories

## P13-01 · Subcontractors & procurement · Must

**Role:** Procurement  
**Story:** As a procurement, I want material requests generated from approved selections and estimates, so that purchasing starts from real needs.

**Acceptance criteria**

1. Given approved selections and estimate lines, when I generate requests, then Material Requests per project and stage with needed-by dates are created.

## P13-02 · Subcontractors & procurement · Must

**Role:** Procurement  
**Story:** As a procurement, I want to compare supplier quotations, so that I buy at the best price.

**Acceptance criteria**

1. Given an RFQ sent to 3 suppliers with their quotations entered, when I open the comparison, then I see prices side by side and can create a PO from the chosen one.

## P13-03 · Subcontractors & procurement · Must

**Role:** Procurement  
**Story:** As a procurement, I want purchase orders linked to project and stage, so that committed costs are visible.

**Acceptance criteria**

1. Given a PO with project and stage, when it is submitted, then the committed cost report includes it under that project and stage.

## P13-04 · Subcontractors & procurement · Must

**Role:** Engineer  
**Story:** As an engineer, I want to confirm deliveries on site with a photo, so that we pay only for what arrived.

**Acceptance criteria**

1. Given a PO delivered to site, when I confirm receipt with a photo of the delivery note, then a Purchase Receipt is created with the photo attached.

## P13-05 · Subcontractors & procurement · Must

**Role:** Admin  
**Story:** As an admin, I want signed subcontracts with retention and advance, so that terms are clear and enforceable.

**Acceptance criteria**

1. Given a subcontract with lines, 10% retention and an advance, when it is signed, then it becomes active and cannot be edited.

## P13-06 · Subcontractors & procurement · Must

**Role:** Engineer  
**Story:** As an engineer, I want subcontractor progress claims (مستخلصات) with automatic previous quantities, so that claims are fast and correct.

**Acceptance criteria**

1. Given 3 consecutive claims with retention and advance recovery, when each is approved, then net due matches the hand calculation and a Purchase Invoice is created.
2. Given a claim exceeding contract quantity, when I submit without admin override, then it is blocked.

## P13-07 · Subcontractors & procurement · Should

**Role:** Accountant  
**Story:** As an accountant, I want to release retention at project end, so that subcontractors are paid what is held.

**Acceptance criteria**

1. Given retention held on approved claims, when I release it, then a payment is created and retention payable in the ledger becomes zero.
