# Phase 8 stories

## P08-01 · Proposals & e-signature · Must

**Role:** Admin  
**Story:** As an admin, I want to send a proposal or contract for e-signature, so that the client can sign without visiting.

**Acceptance criteria**

1. Given an approved quotation and a contract template, when I press ابعت للتوقيع, then an Arabic PDF is stored privately with its hash and the client is notified by email and portal.

## P08-02 · Proposals & e-signature · Must

**Role:** Client  
**Story:** As a client, I want to sign on my phone with a code, so that signing is quick and secure.

**Acceptance criteria**

1. Given a signature request, when I read it, request the code, enter it and draw my signature, then the request becomes Signed and every step is logged with time and IP.
2. Given I enter a wrong code 3 times, when I try a 4th time, then the request is locked until the office resends it.

## P08-03 · Proposals & e-signature · Must

**Role:** Owner  
**Story:** As an owner, I want signed documents frozen and verifiable, so that they hold up in a dispute.

**Acceptance criteria**

1. Given a signed request, when anyone tries to change it or its file, then the change is rejected.
2. Given the stored PDF is altered, when I run Verify, then it reports the hash does not match.

## P08-04 · Proposals & e-signature · Must

**Role:** Admin  
**Story:** As an admin, I want signing a contract to set up the project automatically, so that no double data entry.

**Acceptance criteria**

1. Given a contract is signed, when the kickoff runs, then the project, stages with weights, tasks and payment milestones exist and the client is on the project.

## P08-05 · Proposals & e-signature · Should

**Role:** Client  
**Story:** As a client, I want to decline with a reason, so that the office knows what to change.

**Acceptance criteria**

1. Given a signature request, when I press Decline and enter a reason, then the admin is notified with the reason.

## P08-06 · Proposals & e-signature · Should

**Role:** Admin  
**Story:** As an admin, I want requests to expire, so that old offers are not signed by mistake.

**Acceptance criteria**

1. Given a request past its expiry date, when the daily job runs, then it becomes Expired and cannot be signed.
