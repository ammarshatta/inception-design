# Phase 5 stories

## P05-01 · Public site & leads · Must

**Role:** Visitor  
**Story:** As a visitor, I want to browse apartment designs with filters, so that I find a design that fits my apartment.

**Acceptance criteria**

1. Given published designs, when I filter by area, bedrooms, style and price and sort, then only matching designs show, 12 per page.
2. Given an unpublished design, when I open its URL, then I get 404.

## P05-02 · Public site & leads · Must

**Role:** Visitor  
**Story:** As a visitor, I want a design page with images, floor plan, stages, duration and estimated cost, so that I understand what I would get.

**Acceptance criteria**

1. Given a published design, when I open it, then I see its gallery, floor plan, execution stages, duration and cost range.

## P05-03 · Public site & leads · Must

**Role:** Visitor  
**Story:** As a visitor, I want to request implementation of a design, so that the office contacts me.

**Acceptance criteria**

1. Given the request form with valid name, Egyptian mobile, governorate and area, when I submit, then a Lead linked to the design is created and the admin is emailed.
2. Given 5 requests from my IP in the last hour, when I submit a 6th, then it is rejected with a friendly message.

## P05-04 · Public site & leads · Should

**Role:** Visitor  
**Story:** As a visitor, I want to view a published project, so that I trust the office's work.

**Acceptance criteria**

1. Given a public project with photos set to publishable only, when I open it, then I see only publishable photos and no phone, email, amounts or client name unless allowed.
2. Given a private project, when I open its slug, then I get the same 404 as for a missing project.

## P05-05 · Public site & leads · Must

**Role:** Visitor  
**Story:** As a visitor, I want privacy and data-deletion pages in Arabic, so that I know how my data is used.

**Acceptance criteria**

1. Given the public site, when I open /privacy or /data-deletion, then I see the current Arabic text with contact details from Settings.

## P05-06 · Public site & leads · Must

**Role:** Admin  
**Story:** As an admin, I want to remove demo content with one command before launch, so that no sample data reaches real clients.

**Acceptance criteria**

1. Given the demo design is installed, when I run the demo removal command, then the demo design and its files are gone.
