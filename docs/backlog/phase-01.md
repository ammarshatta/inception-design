# Phase 1 stories

## P01-01 · Data model & permissions · Must

**Role:** Engineer  
**Story:** As an engineer, I want to see only the projects I am assigned to, so that client data stays private between teams.

**Acceptance criteria**

1. Given I am not in a project's team (Project User), when I open that project by URL or API, then I get a permission error.
2. Given I am not in a project's team, when I list projects, then that project is not in the list.

## P01-02 · Data model & permissions · Must

**Role:** Client  
**Story:** As a client, I want to see only my own projects and never internal notes, so that I see what concerns me and nothing confidential.

**Acceptance criteria**

1. Given another client's project, when I request it by ID, then I get a permission error.
2. Given an update marked internal only on my project, when I list or open updates, then that update and its photos are not returned.

## P01-03 · Data model & permissions · Must

**Role:** Admin  
**Story:** As an admin, I want project progress calculated from weighted stages, so that the percentage reflects real work, not a simple average.

**Acceptance criteria**

1. Given stage A weight 5 is Done and stage B weight 30 is at 50%, others at 0, when progress is recalculated, then the project shows 20.0%.
2. Given an Auto stage with 4 checklist items, 3 ticked, when the stage is saved, then its progress is 75%.
3. Given stage weights that add up to 90, when I open the project, then I see a warning that weights do not total 100.

## P01-04 · Data model & permissions · Must

**Role:** Admin  
**Story:** As an admin, I want a new project to copy the stages of a template, so that I do not re-type stages for every project.

**Acceptance criteria**

1. Given a template with 8 stages and checklists, when I create a project from it, then the project has 8 stages with the same names, weights and checklists.
2. Given a project created from a template, when I later edit the template, then the existing project's stages do not change.

## P01-05 · Data model & permissions · Must

**Role:** Admin  
**Story:** As an admin, I want office name, logo, colors and terms stored in one settings page, so that the product can serve other offices later (SaaS).

**Acceptance criteria**

1. Given Inceptiondesign Settings has a logo and office name, when any page, email or PDF is rendered, then it uses those values.
2. Given the codebase, when the hardcoded-branding test runs, then it fails if the office name appears literally in templates or Python.

## P01-06 · Data model & permissions · Must

**Role:** Client  
**Story:** As a client, I want an approval I answered to be locked, so that nobody can change what I agreed to.

**Acceptance criteria**

1. Given an approval I answered, when anyone, including the admin, tries to edit it, then the change is rejected.
