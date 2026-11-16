# Phase 4 — Client portal

**Status:** 🔵 Code written on 16 Nov 2026; waiting for CI.

## What was done

| Task | Where |
|---|---|
| API: `client_home`, `timeline`, `gallery`, `payments`, `invoice_pdf`, `messages`, `send_message`, `request_approval`, `answer_approval`. Each one calls `assert_project_access`. Updates are read through `get_list`, so the internal-only filter applies everywhere. | `api/portal.py` |
| Client screens, with the 5-tab bottom navigation from the design board: Home, Timeline (planned vs actual and delay in days), Gallery (stage filter, newest first, lightbox), Payments (totals, status pills, invoice PDF), Chat (text, photos, approval cards with موافق / عندي سؤال) | `frontend/src/pages/Client*.vue`, `ChatPage.vue`, `components/ClientNav.vue` |
| A client with one project lands straight on its home page. Engineers open the same chat from the project page. | `Home.vue`, `ProjectPage.vue` |
| Arabic RTL invoice print format "Inceptiondesign Invoice" (branding comes from Settings) | `print_format/inceptiondesign_invoice/` |
| Realtime: each new message is published with `publish_realtime(..., user=<member>)` to every project member | `notifications.py` |
| Notifications (Notification Log, which also emails when an outgoing account exists): new non-internal update, stage done, new message, approval requested, milestone due | `notifications.py`, `hooks.py` |

## Decisions

1. **Realtime goes to each member, not to a custom room.** The plan allows this fallback, and it means only project members can receive the event. The portal also polls every 3 seconds while the chat is open, so messages arrive within 5 seconds even without a socket server (as in CI's `bench serve`). A socket client in the portal can be added later. It isn't needed to meet the 5-second target.
2. **Photos in the chat:** the client uploads the photo privately and unattached. `send_message` then attaches it to the message, and only when the uploader is the current user.
3. **The invoice PDF is served through `invoice_pdf(milestone)`.** Clients have no Sales Invoice permission. The project check and the milestone check stand in for it.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Changing an answered approval through the API fails, even for the admin | `test_client_portal.test_chat_and_approval_flow`, `test_approvals.py` | pending CI |
| Two browsers: a message appears for the other user within 5 seconds | `e2e/chat.spec.ts` | pending CI |
| Every portal method rejects another client's project (one subtest per method) | `test_every_method_rejects_other_project`, `test_answer_approval_other_project_rejected` | pending CI |
| An internal update never appears on home, in the gallery or in notifications | `test_home_shows_last_three_non_internal`, `test_internal_never_in_gallery`, `test_update_notifies_client_internal_does_not` | pending CI |
| The invoice PDF renders in Arabic RTL (screenshot) | CI renders the PDF with PlutoPrint (Frappe v16's built-in engine; the CI image has no wkhtmltopdf) and turns it into a PNG: `docs/progress/screens/` | pending CI |
| P04-02: a 4-day delay is shown | `test_timeline_delay` | pending CI |
