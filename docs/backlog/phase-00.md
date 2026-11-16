# Phase 0 stories

## P00-01 · Foundation · Must

**Role:** Owner  
**Story:** As an owner, I want the app installed on my computer with automated tests on every push, so that I know each change works before it goes further.

**Acceptance criteria**

1. Given a fresh clone of the repo, when a commit is pushed to main, then GitHub Actions installs ERPNext v16 and construction_core on a new site and all tests pass.
2. Given a failing test, when a commit is pushed, then the CI run is red and the commit is marked failed.

## P00-02 · Foundation · Must

**Role:** Any user  
**Story:** As any user, I want to open the portal at /portal in Arabic, so that the app feels native to me.

**Acceptance criteria**

1. Given I am logged in, when I open /portal, then I see "أهلاً، <my full name>" in a right-to-left layout.
2. Given I am logged out, when I open /portal, then I am redirected to /login and back to /portal after logging in.

## P00-03 · Foundation · Should

**Role:** Owner  
**Story:** As an owner, I want a versions and licenses report, so that I know exactly what the product depends on.

**Acceptance criteria**

1. Given phase 0 is complete, when I open docs/versions.md, then it lists frappe, erpnext, frappe_docker and frappe-ui with exact version, license and release date.
