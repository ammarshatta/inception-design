# Phase 2 stories

## P02-01 · Admin & client onboarding · Must

**Role:** Admin  
**Story:** As an admin, I want to arrange a project's stages, weights and dates in one screen, so that setting up a project takes minutes.

**Acceptance criteria**

1. Given a project, when I add, reorder or edit stages in the Stages section, then the changes save and the weight total updates.
2. Given a new admin with a template, when they create a project, add a client and publish it, then it takes under 3 minutes.

## P02-02 · Admin & client onboarding · Must

**Role:** Admin  
**Story:** As an admin, I want to add a client who has an email, so that they can log in without me managing passwords.

**Acceptance criteria**

1. Given the Add Client dialog with name, Egyptian mobile and email, when I confirm, then a Customer, Contact and portal User are created, linked to the project, and a welcome email with a set-password link is sent.
2. Given a mobile number not matching 01[0125]XXXXXXXX, when I confirm, then I see a validation error.

## P02-03 · Admin & client onboarding · Must

**Role:** Admin  
**Story:** As an admin, I want to add a client who has no email, using a username and a WhatsApp message, so that clients without email can still use the portal.

**Acceptance criteria**

1. Given the Add Client dialog without email, when I enter a username and confirm, then a 12-character temporary password is shown once, and a WhatsApp button opens wa.me with the login details.

## P02-04 · Admin & client onboarding · Must

**Role:** Client  
**Story:** As a client, I want to be forced to change a temporary password on first login, so that only I know my password.

**Acceptance criteria**

1. Given my account has a temporary password, when I log in, then I only see the change-password page until I change it.
2. Given I changed my password, when I open /portal, then I reach the portal normally.

## P02-05 · Admin & client onboarding · Must

**Role:** Admin  
**Story:** As an admin, I want to add engineers to a project, so that they can work on it from the portal.

**Acceptance criteria**

1. Given a user with the Construction Engineer role, when I add them with Add Engineer, then they appear in the project team and see it in /portal.

## P02-06 · Admin & client onboarding · Must

**Role:** Admin  
**Story:** As an admin, I want to publish a project by secret link and revoke it, so that I can share progress safely with prospects.

**Acceptance criteria**

1. Given a project set to visibility = link, when I press New Link, then a new link is shown once and the old link returns 404.
2. Given a link with an expiry date in the past, when a visitor opens it, then they get 404.

## P02-07 · Admin & client onboarding · Must

**Role:** Office  
**Story:** As the office, I want nobody to create an account by signing in with Google or Facebook, so that only clients I added can enter.

**Acceptance criteria**

1. Given signup is disabled and an email that is not registered, when someone signs in with Google using it, then no user is created and they see "الحساب ده مش مسجّل، كلّم المكتب".
