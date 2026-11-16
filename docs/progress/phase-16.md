# Phase 16 — Offline mobile and push notifications

**Status:** 🔵 Code written on 17 Nov 2026; waiting for CI.

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate.

## What was built

| Task | Where |
|---|---|
| **Offline queue** in IndexedDB (no library): stage updates, photos (already resized), checklist ticks, daily logs, clock events with the phone's time. Sent in order when online, exponential backoff (2 s … 5 min), photos wait for their update | `frontend/src/lib/idb.ts`, `lib/queue.ts` |
| Exactly once: every item has a UUID; the server's `sync.apply` stores a **Sync Receipt** named by the UUID (unique at the database), so a resend after a closed browser returns the first result; an uploaded photo's URL is kept on the item so it is not uploaded again | `construction_core/sync.py`, `doctype/sync_receipt` |
| Conflict rules: updates, photos and clock events are append-only; daily log is one per day (merge); **checklist: the server wins** when the item changed on the server after the phone's tick — the item is shown as "اترفض" with the reason | `sync._run` |
| Phone time for offline clock events is accepted only through the queue, never from a direct call, and only up to 14 days old | `sitelog.do_clock`, `sync._client_time` |
| **Offline reads**: my projects, project, stage and today's assignments are kept after each successful load; offline the copy is shown with "من غير نت — آخر تحديث: …" | `lib/offline.ts`, `OfflineBanner.vue` |
| The portal page itself works offline (service worker: network first, last copy offline); Background Sync wakes the queue on Android | `api/public.SERVICE_WORKER` (v2) |
| **Sync status**: a badge with the number waiting on the home screen, and `/portal/sync` with each item, its status, attempts, the reason if refused, "جرّب تاني" and (for refused items) "امسح" after a confirm. Nothing is dropped silently | `SyncBadge.vue`, `SyncPage.vue` |
| **Web Push** with VAPID keys from `site_config.json` (see `.env.example`). Pushes carry **no payload**: the service worker asks the server for the newest notification over the logged-in session, so no message text passes through the push service and no extra library is needed (VAPID signing uses `cryptography`, already in Frappe) | `construction_core/push.py` |
| Push on every in-app notification, by category: message, approval (approvals, signatures, change orders), selection, payment, schedule, update. Tapping opens the right portal page | `notifications._notify` → `push.notify` |
| Mute categories per user; turn push on/off per device; "Wi-Fi only" for photos | `/portal/settings` (`SettingsPage.vue`), `push.set_muted`, `lib/queue.wifiOnly` |
| Dead subscriptions (404/410 from the push service) are removed | `push._send_one` |

## Not done / limits

- iOS: Web Push works only for the portal added to the home screen (iOS 16.4+); there is no background sync on iOS, so the queue is sent when the portal is opened.
- Offline creation of a **new** daily log from the page is queued only through the API (the daily-log page itself still needs signal); updates, photos, ticks and clock events are covered.
- "Wi-Fi only" uses `navigator.connection.type`, which Chrome on Android reports; other browsers send photos on any connection.

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Offline: update with 3 photos and a checklist tick, back online, everything arrives exactly once | `e2e/offline.spec.ts` | pending CI |
| Browser killed mid-sync and reopened resumes without duplicates | `test_sync_push.test_same_uuid_twice_creates_one_update`; e2e reloads the page during the sync | pending CI |
| Push received on an Android device for a new message | manual, needs VAPID keys on a real site and a phone | ☐ (owner) |
| Muting a category stops those pushes | `test_muted_category_gets_no_push` | pending CI |
| P16-02: cached projects and assignments offline with the last update time | `e2e/offline.spec.ts` (offline banner) | pending CI |
| P16-03: queue panel lists items with status and retry | `e2e/offline.spec.ts` (5 items listed offline) | pending CI |
