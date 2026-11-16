# Phase 3 stories

## P03-01 · Engineer portal · Must

**Role:** Engineer  
**Story:** As an engineer, I want a list of my projects with progress and current stage, so that I know where to go today.

**Acceptance criteria**

1. Given I am assigned to 3 projects, when I open /portal, then I see 3 cards with name, progress bar, current stage and last update date.

## P03-02 · Engineer portal · Must

**Role:** Engineer  
**Story:** As an engineer, I want to post a stage update with photos from my phone, so that the office and client see progress without calls.

**Acceptance criteria**

1. Given I select 10 photos of 4 MB each on a slow connection, when I submit the update, then every photo uploads with a progress bar and is stored under 500 KB.
2. Given an uploaded photo, when its metadata is inspected, then it contains no GPS location.
3. Given a photo fails to upload 3 times, when the upload stops, then the update shows that photo as failed with a retry button.

## P03-03 · Engineer portal · Must

**Role:** Engineer  
**Story:** As an engineer, I want to tick checklist items on a stage, so that progress updates itself.

**Acceptance criteria**

1. Given an Auto-mode stage, when I tick an item, then the stage and project progress update.

## P03-04 · Engineer portal · Must

**Role:** Engineer  
**Story:** As an engineer, I want to mark an update as internal only, so that I can record problems the client should not see.

**Acceptance criteria**

1. Given an update marked internal only, when the client opens their portal, then the update and its photos are not shown.

## P03-05 · Engineer portal · Should

**Role:** Engineer  
**Story:** As an engineer, I want to mark good photos as suitable for publishing, so that the office can use them in public pages.

**Acceptance criteria**

1. Given a photo, when I toggle مناسبة للنشر, then it becomes available to public pages through a separate public copy.

## P03-06 · Engineer portal · Should

**Role:** Engineer  
**Story:** As an engineer, I want clear limits on videos, so that uploads do not fail silently.

**Acceptance criteria**

1. Given a video longer than 60 s or bigger than 50 MB, when I pick it, then I see an Arabic message explaining the limit and it is not uploaded.

## P03-07 · Engineer portal · Should

**Role:** Engineer  
**Story:** As an engineer, I want to install the portal on my phone's home screen, so that it opens like an app.

**Acceptance criteria**

1. Given Android Chrome, when I choose Install app, then the portal installs and opens full screen with its icon.
