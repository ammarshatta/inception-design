# Phase 7 stories

## P07-01 · Sales & estimating · Must

**Role:** Sales  
**Story:** As a salesperson, I want a Kanban pipeline of opportunities, so that no lead is forgotten.

**Acceptance criteria**

1. Given a Lead from the website, when I convert it, then an Opportunity appears in جديد on the Kanban.
2. Given an opportunity, when I drag it to تسعير, then its stage is saved and the change is logged.

## P07-02 · Sales & estimating · Must

**Role:** Estimator  
**Story:** As an estimator, I want a price library with dated prices and their source, so that estimates use real, traceable prices.

**Acceptance criteria**

1. Given a material with prices dated January and March, when I estimate on a date in February, then the January price is used.
2. Given a price record, when anyone tries to delete it, then it is kept; only a new dated price can supersede it.

## P07-03 · Sales & estimating · Must

**Role:** Estimator  
**Story:** As an estimator, I want reusable assemblies (e.g. one square metre of floor tiling, all-in), so that I estimate fast and consistently.

**Acceptance criteria**

1. Given an assembly with tile, adhesive, grout and labor lines with waste %, when I use it for 50 m², then each component quantity and cost is calculated correctly.

## P07-04 · Sales & estimating · Must

**Role:** Estimator  
**Story:** As an estimator, I want an estimate builder with sections and a live total, so that I produce quotes quickly.

**Acceptance criteria**

1. Given an estimate with material, labor, overhead 10%, profit 15% and VAT, when I save it, then the total equals the engine's known test result to the piastre.

## P07-05 · Sales & estimating · Must

**Role:** Estimator  
**Story:** As an estimator, I want revisions with a comparison, so that changes are traceable.

**Acceptance criteria**

1. Given an approved estimate, when I press Revise, then revision 2 is created and revision 1 is marked Superseded and cannot change.
2. Given two revisions, when I compare them, then added, removed and changed lines are listed with the money difference.

## P07-06 · Sales & estimating · Must

**Role:** Sales  
**Story:** As a salesperson, I want to turn an approved estimate into a Quotation, so that the client receives a formal offer.

**Acceptance criteria**

1. Given an approved estimate, when I press Create Quotation, then an ERPNext Quotation with one line per section is created and linked.

## P07-07 · Sales & estimating · Should

**Role:** Estimator  
**Story:** As an estimator, I want to import prices from Excel, so that I update the library in bulk.

**Acceptance criteria**

1. Given a filled price template, when I import it, then new dated prices are created and errors are reported per row.
