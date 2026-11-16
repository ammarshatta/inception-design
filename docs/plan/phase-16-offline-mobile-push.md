# Phase 16 — Offline mobile and push notifications

## Goal
Engineers and foremen keep working on sites with weak or no signal. The portal queues their work and syncs when they are back online. Everyone gets real phone notifications.

Projul equivalents: the mobile app with offline capability, automatic photo uploads, and mobile notifications.

## Decision
- Keep the **PWA** (installable from Chrome, Android first) instead of App Store and Play Store apps.
- Native store apps are listed as optional in `saas-and-later.md`.
- iOS supports Web Push for installed PWAs, but background sync on iOS is limited: the queue syncs when the app is opened.

## Tasks

1. **Offline queue:**
   - Store pending actions in IndexedDB:
     - stage updates, daily logs, checklist ticks
     - clock events with the local timestamp
     - photos (already resized)
   - A sync worker sends them in order when online, with exponential backoff.
   - Each action carries a client-generated UUID, so server-side inserts are idempotent.
2. **Offline reads:** cache "my projects", the current stages and today's assignments for read-only use offline. Show "آخر تحديث: …".
3. **Conflict rules:**
   - Server data wins for checklists, with the latest timestamp per item.
   - Logs and updates are append-only, so they never conflict.
   - Show a banner if something was rejected, with the reason.
4. **Sync status UI:**
   - A badge with the number of pending items.
   - A list of pending items with retry buttons.
   - Never lose an item silently.
5. **Web Push:**
   - VAPID keys in `.env`, with the subscription stored per user and device.
   - Push for: new message, approval or signature request, selection due, payment due, schedule change.
   - Users can mute categories in the portal settings.
6. **Battery and data:** sync only over Wi-Fi when the user picks "Wi-Fi only" for photos.

## Acceptance criteria
- [ ] Playwright offline mode: create an update with 3 photos and a checklist tick while offline, go online, and everything arrives exactly once.
- [ ] Killing the browser mid-sync and reopening resumes without duplicates (test with UUID idempotency).
- [ ] A push notification is received on an Android device for a new message (manual test, recorded).
- [ ] Muting a category stops those pushes (test).
