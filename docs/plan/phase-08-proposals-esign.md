# Phase 8 — Proposals, e-signature and project kickoff

## Goal
The client receives a professional Arabic proposal or contract in the portal, signs it on their phone, and the signed version is frozen with an audit trail. Signing creates the project, its stages, tasks and payment milestones.

Projul equivalents: e-signature approvals, contracts, and converting estimates into tasks.

## Legal note (for the owner)

The plan builds a **simple electronic signature with a strong audit trail**: drawn signature, email or WhatsApp-link code, time, IP and document hash.

Under Egyptian Law 15/2004, full equivalence to a handwritten signature requires a signature tied to an **ITIDA-licensed certification authority**. Ask a lawyer:
- whether this level is enough for your contracts
- whether you also want a printed, hand-signed copy for large contracts

The design keeps a provider-neutral hook so a licensed e-signature provider can be added later.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `Contract Template` | normal | title, body (Jinja, Arabic), applies_to (Proposal / Contract / Change Order / Selection) |
| `Signature Request` | normal | reference_doctype, reference_name, customer, signer_user, document_pdf (private), pdf_sha256, status (Sent / Viewed / Signed / Declined / Expired), sent_on, expires_on, otp_hash, otp_attempts |
| `Signature Event` | child of Signature Request | event (Sent / Viewed / OTP Sent / Signed / Declined), at, ip, user_agent |
| `Signature Request` fields after signing | — | signature_image (Signature field), signed_on, signed_ip, signed_pdf (PDF with signature page), signed_pdf_sha256 |

## Tasks

1. **Proposal PDF:**
   - An Arabic print format for Quotation, Estimate and contract, built from `Contract Template` and rendered RTL.
   - Office logo and colors come from `Inceptiondesign Settings` (see the SaaS rules in `CLAUDE.md`).
2. **Send for signature:**
   - The admin clicks "ابعت للتوقيع". The system:
     - renders the PDF, stores it **private**, and records its SHA-256
     - creates a `Signature Request`
     - notifies the client by email and in the portal, and shows a `wa.me` link the admin can send
3. **Signing in the portal:**
   - The client opens the request and reads the PDF (pdf.js viewer).
   - The client presses "توقيع" and receives a 6-digit code by email:
     - valid for 10 minutes
     - stored as a hash
     - 3 attempts
   - The client draws a signature (Frappe's Signature control or `signature_pad`, MIT) and confirms.
   - Every step writes a `Signature Event` with IP and user agent.
4. **Freezing:**
   - On signing, the system builds `signed_pdf`: the original pages plus a signature page with:
     - the name, the signature image and the time
     - the IP and both hashes
   - It records `signed_pdf_sha256`.
   - Nothing about a Signed request can change afterwards.
5. **Kickoff on signing a contract:**
   - Create the `Project` from the estimate's design template or sections.
   - Create one `Project Stage` per section, with weights from each section's share of the cost.
   - Create a `Payment Milestone` per contract payment term.
   - Create ERPNext `Task` records per stage (needed for the Gantt in phase 11).
   - Assign the default engineer, and add the client to `Project User`.
6. **Decline:** the client can decline with a reason. The admin is notified.
7. **Expiry:** a scheduler job marks requests Expired after `expires_on`.

## Acceptance criteria
- [ ] Playwright: the client opens the request, gets the code (read from the test mail outbox), signs, and the project with stages, milestones and tasks appears.
- [ ] After signing, every update to the request or its PDF is rejected (test).
- [ ] The SHA-256 of the stored original matches `pdf_sha256`. Tampering with the file is detected by a verify method (test).
- [ ] The 4th wrong code locks the request until the admin resends it (test).
- [ ] The signed PDF renders in Arabic RTL with the signature page (screenshot).
