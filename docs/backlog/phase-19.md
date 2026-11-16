# Phase 19 stories

## P19-01 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want the platform live on my domain over HTTPS, so that clients can use it from anywhere.

**Acceptance criteria**

1. Given the hosting chosen and DNS on Cloudflare, when the stack is deployed, then https://<domain>/app, /portal and the public pages work in Arabic.

## P19-02 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want encrypted daily backups outside the server and a tested restore, so that I never lose client data.

**Acceptance criteria**

1. Given the daily job ran, when I restore the latest backup on another machine using only docs/restore.md, then the site works and the time taken is recorded.
2. Given a backup fails, when the job ends, then I receive an email.

## P19-03 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want one-command deploys with automatic rollback, so that updates are safe.

**Acceptance criteria**

1. Given a release tag that fails its health check, when deploy.sh runs, then the previous version is restored automatically.

## P19-04 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want private files never cached publicly, so that client photos stay private.

**Acceptance criteria**

1. Given a private file URL, when it is requested through Cloudflare, then the response is never a cache HIT.

## P19-05 · Launch & compliance · Should

**Role:** Client  
**Story:** As a client, I want to sign in with Google or Facebook on the live site, so that I do not need another password.

**Acceptance criteria**

1. Given my registered email, when I sign in with Google or Facebook, then I reach my portal.
2. Given an unknown Google account, when it signs in, then access is refused and no account is created.

## P19-06 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want data-protection obligations settled before launch, so that the business complies with Egypt's PDPL.

**Acceptance criteria**

1. Given the checklist in phase 19, when launch is prepared, then licence, data location, DPO, notices, breach plan and data register each have a recorded answer.

## P19-07 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want uptime and disk alerts, so that I know about problems before clients do.

**Acceptance criteria**

1. Given the site is down for 5 minutes or the disk passes 80%, when monitoring checks, then I receive an email.

## P19-08 · Launch & compliance · Must

**Role:** Owner  
**Story:** As an owner, I want live integrations switched on one at a time and tested, so that nothing breaks at launch.

**Acceptance criteria**

1. Given gateway, push, AI and GPS are configured, when each is switched on, then its live test passes and is recorded before the next one.
