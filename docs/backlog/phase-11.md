# Phase 11 stories

## P11-01 · Scheduling & crews · Must

**Role:** Engineer  
**Story:** As an engineer, I want a Gantt chart of project tasks with dependencies, so that I plan and adjust visually.

**Acceptance criteria**

1. Given a project with tasks, when I drag a task to new dates, then the dates save and the parent stage's planned dates update.

## P11-02 · Scheduling & crews · Must

**Role:** Admin  
**Story:** As an admin, I want a company calendar of crew and subcontractor assignments, so that I see who is where.

**Acceptance criteria**

1. Given assignments across projects, when I open the calendar and filter by crew, then I see that crew's assignments in day, week or month view.

## P11-03 · Scheduling & crews · Must

**Role:** Admin  
**Story:** As an admin, I want warnings when a crew is double-booked, so that I avoid idle sites and angry clients.

**Acceptance criteria**

1. Given a crew assigned to project A on days 1-5, when I assign it to project B on day 3, then I see a warning naming project A; if I override, it is logged.

## P11-04 · Scheduling & crews · Must

**Role:** Engineer  
**Story:** As an engineer, I want to delay a task and move everything that depends on it, so that the schedule stays consistent.

**Acceptance criteria**

1. Given a chain of 3 dependent tasks and a Friday in between, when I postpone the first by 2 working days, then the preview and saved dates skip Fridays and holidays, and the client and foremen are notified.

## P11-05 · Scheduling & crews · Must

**Role:** Foreman  
**Story:** As a foreman, I want to see my crew's work for today and this week, so that I know where to take the team.

**Acceptance criteria**

1. Given I am a foreman, when I open شغلي النهارده, then I see only my crew's assignments with address and map link.

## P11-06 · Scheduling & crews · Should

**Role:** Admin  
**Story:** As an admin, I want Fridays and Egyptian public holidays in the calendar, so that dates are realistic.

**Acceptance criteria**

1. Given the holiday list for the year, when dates are calculated, then holidays are skipped as non-working days.
