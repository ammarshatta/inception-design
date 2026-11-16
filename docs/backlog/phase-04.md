# Phase 4 stories

## P04-01 · Client portal · Must

**Role:** Client  
**Story:** As a client, I want a home screen with progress, current stage, latest updates and next payment, so that I understand my project at a glance.

**Acceptance criteria**

1. Given my project, when I open /portal, then I see overall progress, current stage, the last 3 non-internal updates and the next payment amount.

## P04-02 · Client portal · Must

**Role:** Client  
**Story:** As a client, I want a timeline of stages with planned and actual dates, so that I know if the project is late.

**Acceptance criteria**

1. Given a stage that finished 4 days after its planned end, when I open the timeline, then it shows a 4-day delay.

## P04-03 · Client portal · Must

**Role:** Client  
**Story:** As a client, I want a gallery of site photos grouped by stage and date, so that I can follow the work visually.

**Acceptance criteria**

1. Given photos on several stages, when I open the gallery and filter by a stage, then I see only that stage's photos, newest first, with a lightbox.

## P04-04 · Client portal · Must

**Role:** Client  
**Story:** As a client, I want to see my payments and download invoices in Arabic, so that I know what I owe and have records.

**Acceptance criteria**

1. Given a milestone with a submitted invoice, when I open Payments, then I see its status and can download an Arabic RTL PDF invoice.

## P04-05 · Client portal · Must

**Role:** Client  
**Story:** As a client, I want to chat with my engineer with photos, so that questions are answered in one place.

**Acceptance criteria**

1. Given the engineer and I both have the chat open, when I send a message, then the engineer sees it within 5 seconds.
2. Given another client's project ID, when I try to send or read messages there, then the request is rejected.

## P04-06 · Client portal · Must

**Role:** Engineer  
**Story:** As an engineer, I want to ask the client for an approval in the chat, so that decisions are recorded.

**Acceptance criteria**

1. Given I send an approval request with title, details and amount, when the client presses موافق or عندي سؤال, then the answer and time are shown and can no longer change.

## P04-07 · Client portal · Should

**Role:** Client  
**Story:** As a client, I want notifications for updates, finished stages, messages, approvals and due payments, so that I never miss anything.

**Acceptance criteria**

1. Given a new non-internal update, when it is saved, then I get an email and an in-portal notification.
2. Given an internal update, when it is saved, then I get no notification.
