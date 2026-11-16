# Phase 10 stories

## P10-01 · Change orders · Must

**Role:** Client  
**Story:** As a client, I want to request a change from the portal with photos, so that my request is recorded and priced.

**Acceptance criteria**

1. Given my project, when I submit اطلب تعديل with a description and 2 photos, then a Draft change order is created and the engineer and admin are notified.

## P10-02 · Change orders · Should

**Role:** Engineer  
**Story:** As an engineer, I want to create a change order on site, so that issues found on site are captured immediately.

**Acceptance criteria**

1. Given the portal on my phone, when I create a change order with photos, then a Draft appears for pricing in the office.

## P10-03 · Change orders · Must

**Role:** Estimator  
**Story:** As an estimator, I want change orders priced by the costing engine, so that prices are consistent and traceable.

**Acceptance criteria**

1. Given change order lines including a removal, when I save, then the cost difference is calculated by the engine and cannot be typed by hand.

## P10-04 · Change orders · Must

**Role:** Client  
**Story:** As a client, I want to review and sign change orders, so that nothing changes my price without my consent.

**Acceptance criteria**

1. Given a change order sent to me, when I sign it, then it becomes Approved, and a payment milestone for the difference is created.
2. Given a change order sent to me, when I reject it with a reason, then it becomes Rejected and keeps its history.

## P10-05 · Change orders · Must

**Role:** Accountant  
**Story:** As an accountant, I want negative change orders to produce a credit, so that the client is billed correctly.

**Acceptance criteria**

1. Given an approved change order of -3,000 EGP, when it is processed, then a credit is created and the receivables report shows it.

## P10-06 · Change orders · Must

**Role:** Owner  
**Story:** As an owner, I want approved changes to update budget and schedule, so that plans stay realistic.

**Acceptance criteria**

1. Given an approved change order with +5 days impact, when it is approved, then the project budget increases by the difference and dependent stages move 5 working days.
