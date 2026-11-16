# Phase 6 stories

## P06-01 · Money · Must

**Role:** Accountant  
**Story:** As an accountant, I want to invoice a due milestone in one click, so that billing follows progress.

**Acceptance criteria**

1. Given a milestone that became Due, when I press اعمل فاتورة, then a draft Sales Invoice for the customer, project and amount is created.
2. Given I submit that invoice, when it is submitted, then the milestone becomes Invoiced and links the invoice.

## P06-02 · Money · Must

**Role:** Accountant  
**Story:** As an accountant, I want collections to mark milestones as paid, so that the client portal is always accurate.

**Acceptance criteria**

1. Given an invoiced milestone, when I submit a Payment Entry that fully pays the invoice, then the milestone becomes Paid and the client sees Paid.
2. Given that Payment Entry, when I cancel it, then the milestone returns to Invoiced.

## P06-03 · Money · Must

**Role:** Accountant  
**Story:** As an accountant, I want to record site expenses by project and stage, so that I see where money goes.

**Acceptance criteria**

1. Given a Purchase Invoice with project and stage, when I submit it, then its cost appears under that project and stage in reports.

## P06-04 · Money · Must

**Role:** Accountant  
**Story:** As an accountant, I want VAT applied from a template I control, so that tax is correct without code changes.

**Acceptance criteria**

1. Given a VAT template with the rate I entered, when I apply it to an invoice, then tax is calculated at that rate.

## P06-05 · Money · Must

**Role:** Owner  
**Story:** As an owner, I want a financial summary per project, so that I know contract value, billed, collected, spent and outstanding.

**Acceptance criteria**

1. Given a sample project with invoices, payments and expenses, when I run the report, then its totals equal the General Ledger and Receivables to the piastre.
