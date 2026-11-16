# Phase 17 stories

## P17-01 · Reports & dashboards · Must

**Role:** Owner  
**Story:** As an owner, I want a WIP report with earned value and over/under billing, so that I know which projects make or lose money.

**Acceptance criteria**

1. Given a seeded project with known numbers, when I run WIP, then earned value, billed to date and over/under billing match the expected values.

## P17-02 · Reports & dashboards · Must

**Role:** Owner  
**Story:** As an owner, I want job costing by stage: budget, committed, actual, so that I spot overruns early.

**Acceptance criteria**

1. Given POs, subcontracts and invoices on a project, when I run job costing, then committed and actual match the source documents and ERPNext reports.

## P17-03 · Reports & dashboards · Should

**Role:** Owner  
**Story:** As an owner, I want a labor report by project, crew and employee, so that I control labor cost.

**Acceptance criteria**

1. Given timesheets and flagged clock events, when I run the labor report, then hours, cost and out-of-area flags are shown per project and crew.

## P17-04 · Reports & dashboards · Should

**Role:** Sales  
**Story:** As a salesperson, I want pipeline and conversion reports, so that I improve how we win work.

**Acceptance criteria**

1. Given opportunities across stages and outcomes, when I run the pipeline report, then I see counts per stage, conversion rate, win/loss reasons and lead source.

## P17-05 · Reports & dashboards · Must

**Role:** Owner  
**Story:** As an owner, I want a manager dashboard with key numbers, so that I see the business on one page.

**Acceptance criteria**

1. Given live data, when I open لوحة المدير, then I see active projects, WIP, receivables, overdue, late projects and pipeline value, each drilling down to its source.

## P17-06 · Reports & dashboards · Should

**Role:** Engineer  
**Story:** As an engineer, I want my own dashboard in the portal, so that I know my priorities.

**Acceptance criteria**

1. Given I am an engineer, when I open my dashboard, then I see only my projects, today's tasks, overdue selections and pending approvals.

## P17-07 · Reports & dashboards · Could

**Role:** Owner  
**Story:** As an owner, I want a weekly summary by email, so that I stay informed without logging in.

**Acceptance criteria**

1. Given Saturday 9 AM, when the scheduler runs, then I receive a PDF summary.
2. Given 200 seeded projects, when any report runs, then it finishes in under 3 seconds.
