# Known limitations (v1)

- iOS: Web Push only for the portal added to the home screen (iOS 16.4+); no background sync, so the offline queue is sent when the portal is opened.
- Takeoff: page 1 of a PDF; markup on images only.
- Online payments: full outstanding of a milestone per payment; Paymob only (other gateways plug into `payments/gateway.py`).
- Desk chat panel for the assistant not built; office users use `/portal/assistant`.
- Report names in the desk are English internal names; the "لوحة المدير" shortcuts show Arabic names.
- Islamic holidays must be added to "إجازات المقاولات" every year (they move).
- Items are non-stock: receipts confirm deliveries but move no stock.
