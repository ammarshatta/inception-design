# Phase 12 stories

## P12-01 · Daily logs & time · Must

**Role:** Engineer  
**Story:** As an engineer, I want a daily log of manpower, work done, materials, issues and photos, so that every site day is documented.

**Acceptance criteria**

1. Given today's log already exists for the project, when I open the daily log, then I edit the same log, prefilled from yesterday where useful.

## P12-02 · Daily logs & time · Must

**Role:** Foreman  
**Story:** As a foreman, I want to clock my crew in and out with location, so that hours are trusted without paper.

**Acceptance criteria**

1. Given I accepted the Arabic consent notice, when I clock in within 150 m of the site, then a clock event is saved as inside the site area.
2. Given I am 400 m away, when I clock in, then the event is saved and flagged for engineer approval.
3. Given I have not accepted consent, when I try to clock in, then I am shown the consent notice first and nothing is recorded.

## P12-03 · Daily logs & time · Must

**Role:** Accountant  
**Story:** As an accountant, I want timesheets built from clock events and costed, so that labor cost lands on the project.

**Acceptance criteria**

1. Given matched in and out events, when the nightly job runs and the engineer submits, then a Timesheet is created and the project's labor cost rises by hours × rate.
2. Given an In without an Out, when the job runs, then it is flagged and not counted.

## P12-04 · Daily logs & time · Should

**Role:** Client  
**Story:** As a client, I want to see daily logs of my project without costs, so that I see work happening every day.

**Acceptance criteria**

1. Given a non-internal daily log, when I open it, then I see work done and photos but no manpower costs.

## P12-05 · Daily logs & time · Could

**Role:** Client  
**Story:** As a client, I want a weekly summary PDF, so that I get a simple progress report.

**Acceptance criteria**

1. Given a week of logs, when the weekly job runs, then I receive an Arabic PDF with days worked, progress and photos.
