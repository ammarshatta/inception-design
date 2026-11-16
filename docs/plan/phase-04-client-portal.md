# Phase 4 — Client portal

## Goal
A client opens `/portal` and sees:
- how the project is going
- the photos
- the payments

The client can also chat with the engineer and answer approval requests.

## Tasks

1. **API** in `api/portal.py`. Each method checks access and never returns `internal_only` content to clients:
   - `client_home(project)`
   - `timeline(project)`
   - `gallery(project, stage=None)`
   - `payments(project)`
   - `messages(project, before=None, limit=30)`
   - `send_message(project, text, file_url=None)`
   - `request_approval(project, title, detail, amount=None)` — engineers and admins only
   - `answer_approval(message, answer)` — the answer is `Approved` or `Question`
2. **Screens:**
   - **Home:** overall progress, current stage, last 3 updates, and the next payment with its amount.
   - **Timeline:** every stage with planned and actual dates, and the delay in days.
   - **Gallery:** photos grouped by stage and date, with a lightbox.
   - **Payments:**
     - the milestones and their status
     - the linked `Sales Invoice`, downloadable as PDF with an Arabic print format (created in this phase)
   - **Chat:**
     - text and image messages
     - an approval shows as a card with "موافق" and "عندي سؤال" buttons
     - after it is answered, the card shows the answer and the time
3. **Realtime:**
   - On `Project Message.after_insert`, call `frappe.publish_realtime` with event `project_message` and `room=f"project:{project}"`. Frappe supports custom rooms; check how in v16.
   - Make sure only users with access to the project can join that room. If v16 cannot restrict custom rooms, publish to each allowed user (`user=`) instead.
4. **Notifications** (Frappe Notification + `Notification Log`, plus email through the default outgoing account) for:
   - a new non-internal update
   - a stage done
   - a new message
   - an approval requested
   - a milestone due

## Acceptance criteria
- [ ] Changing an answered approval through the API fails, even for an admin (test).
- [ ] Playwright with two browsers: a message appears for the other user within 5 seconds.
- [ ] Every portal method rejects a project the client does not belong to (one test per method).
- [ ] An `internal_only` update never appears on home, gallery or notifications for the client (test).
- [ ] The invoice PDF renders correctly in Arabic RTL (attach a screenshot).
