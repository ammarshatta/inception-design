# Phase 16 stories

## P16-01 · Offline mobile & push · Must

**Role:** Engineer  
**Story:** As an engineer, I want to record updates, logs and photos without signal, so that weak coverage on site does not stop me.

**Acceptance criteria**

1. Given I am offline, when I create an update with 3 photos and tick an item, then they are queued and sent exactly once when I am back online.
2. Given the browser is closed mid-sync, when I reopen it, then syncing resumes without duplicates.

## P16-02 · Offline mobile & push · Should

**Role:** Engineer  
**Story:** As an engineer, I want to read my projects and today's tasks offline, so that I have what I need on site.

**Acceptance criteria**

1. Given I opened the portal online earlier, when I open it offline, then I see cached projects and assignments with the last update time.

## P16-03 · Offline mobile & push · Must

**Role:** Engineer  
**Story:** As an engineer, I want to see what is still waiting to sync, so that I trust nothing is lost.

**Acceptance criteria**

1. Given 2 items in the queue, when I open the sync panel, then I see both with status and can retry a failed one.

## P16-04 · Offline mobile & push · Must

**Role:** Any user  
**Story:** As any user, I want push notifications on my phone, so that I react quickly.

**Acceptance criteria**

1. Given I enabled notifications on Android, when someone sends me a message, then I get a push notification that opens the chat.

## P16-05 · Offline mobile & push · Should

**Role:** Any user  
**Story:** As any user, I want to mute notification categories, so that I only get what matters to me.

**Acceptance criteria**

1. Given I muted payment reminders, when a reminder is due, then no push is sent to me for it.

## P16-06 · Offline mobile & push · Could

**Role:** Engineer  
**Story:** As an engineer, I want an option to upload photos on Wi-Fi only, so that I save mobile data.

**Acceptance criteria**

1. Given Wi-Fi only is on and I am on mobile data, when I add photos, then they wait in the queue until I am on Wi-Fi.
