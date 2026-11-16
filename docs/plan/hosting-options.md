# Hosting (decide before phase 19)

- **Phases 0–18:** everything runs on the owner's computer, at no cost.
- **Phase 19 (launch day):** hosting starts on a server outside the office.

| Option | Monthly cost | Pros | Cons |
|---|---|---|---|
| **VPS, self-managed (recommended)** | ~€5–9 | Always on, fast and cheap. We control everything. <br>• **Contabo Cloud VPS 10** (8 GB RAM): ~€4.50–5.50 on a 12-month term. <br>• **Hetzner CX33** (4 vCPU, 8 GB, 80 GB): €8.49 + €0.50 IPv4, excl. VAT. It was not orderable on 20 Oct 2026 (capacity), so check again. Steadier performance than Contabo. | We run updates and backups. Both are scripted in phase 19. |
| **Frappe Cloud** | from ~$25 | Managed by Frappe: upgrades, backups and SSL. Least maintenance. | Custom apps need a private bench, so about $25/month minimum. Less control over the server. |

## Important: where the data lives (Egypt PDPL)

Egypt's data protection law requires a licence to transfer personal data outside Egypt; the cross-border licence applies to cloud storage abroad as well. Contabo, Hetzner, Frappe Cloud and R2 are all outside Egypt. Before launch, a lawyer decides between:
- **getting the licence**, and keeping the options above
- **hosting in Egypt:** some providers sell VPS in Cairo (for example LightNode lists a Cairo location with a 4 vCPU / 8 GB plan, billed hourly). Prices are higher and less transparent, so get quotes first. Backups would then also need to stay in Egypt.

## Recommendation

A VPS with at least 8 GB RAM. Choose Frappe Cloud only if nobody will look after a server. The final location depends on the lawyer's answer above.

## Free services used with the VPS

- **Cloudflare (Free):** DNS, HTTPS and CDN, with a cache-bypass rule for private paths.
- **Cloudflare R2:** encrypted daily backups. The first 10 GB are free, with no egress fees.
- **Brevo (Free):** outgoing email, up to 300 emails a day.
- **Google Cloud and Meta for Developers:** OAuth apps for Google and Facebook login. Free.

## Costs from launch

- **Domain:** about $11/year for a `.com` on Cloudflare Registrar.
- **Server:** about €5–9 per month.

Until launch, the only cost is your own computer. GitHub private repos and Actions are free within the monthly limits.

## Things that add cost (only with approval)

- **WhatsApp Business API or SMS:** charged per message. The plan uses free `wa.me` links instead.
- **Egyptian Tax Authority e-invoicing:** commercial apps exist; one is listed from $999 one-time. Ask your accountant.
- **A bigger server, if 8 GB is not enough:** Contabo VPS 20 (12 GB) costs about €1.50/month more. With all phases on, start with 12 GB if the budget allows.
- **Online card and wallet payments:** a fee per transaction; one public listing shows Paymob at 2.75%. Confirm with the provider.
- **AI assistant:** pay-per-use, limited by the monthly cap in `AI Settings`.
- **A licensed e-signature provider:** only if the lawyer says the built-in signature is not enough.
