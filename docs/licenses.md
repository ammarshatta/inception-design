# Licences of what we ship

| Component | Licence | Notes |
|---|---|---|
| Frappe Framework v16 | MIT | |
| ERPNext v16 | GPL-3.0 | We do not modify it; our app is separate |
| construction_core (this app) | owner's | |
| frappe-ui | MIT | portal UI |
| Vue 3, vue-router | MIT | |
| Tailwind CSS | MIT | |
| pdf.js (`pdfjs-dist` 3.11.174) | Apache-2.0 | takeoff page; `isEvalSupported: false` |
| pypdf | BSD-3-Clause | signed PDFs (ships with Frappe) |
| PlutoPrint | MIT | PDF engine in Frappe v16 |
| Pillow | MIT-CMU | photo resizing (ships with Frappe) |
| cryptography | Apache-2.0 / BSD | Web Push VAPID signing (ships with Frappe) |
| Playwright (tests only) | Apache-2.0 | not deployed |

No AGPL component is used (rule 15). Markup and the offline queue use no library.
