# Phase 14 stories

## P14-01 · Documents, markup & takeoff · Must

**Role:** Engineer  
**Story:** As an engineer, I want a document library per project with versions, so that everyone uses the current drawing.

**Acceptance criteria**

1. Given a drawing with version 1, when I upload version 2, then version 2 becomes current and version 1 stays downloadable.

## P14-02 · Documents, markup & takeoff · Must

**Role:** Client  
**Story:** As a client, I want to see the documents the office shares with me, so that I have my contract and drawings at hand.

**Acceptance criteria**

1. Given documents marked visible and not visible, when I open Documents, then I see only visible ones at their current version.
2. Given a non-visible document's URL, when I open it, then access is denied.

## P14-03 · Documents, markup & takeoff · Should

**Role:** Engineer  
**Story:** As an engineer, I want to draw and write on photos and plans, so that I explain issues clearly.

**Acceptance criteria**

1. Given a site photo, when I add arrows and Arabic text and save, then a marked-up copy is saved, editable later, and the original is unchanged.

## P14-04 · Documents, markup & takeoff · Must

**Role:** Estimator  
**Story:** As an estimator, I want to measure lengths and areas on a drawing, so that quantities come from the plan.

**Acceptance criteria**

1. Given a PDF floor plan, when I calibrate a known 5 m wall and draw a 4×5 m room, then the measured area is 20 m².
2. Given a measured area, when I press أضف للتسعير, then it becomes the quantity of an estimate line.
