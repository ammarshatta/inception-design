"""The only module with allow_guest=True (CLAUDE.md rule 5).

Everything here returns an explicit allowlist of fields.
"""

import json

import frappe
from werkzeug.wrappers import Response

from construction_core.branding import get_branding

SW_VERSION = "cc-portal-v1"


@frappe.whitelist(allow_guest=True)
def manifest():
	"""Web app manifest for the portal; the name comes from Settings (SaaS rule)."""
	b = get_branding()
	name = b["office_name"] or "Portal"
	data = {
		"name": name,
		"short_name": name[:12],
		"start_url": "/portal/",
		"scope": "/portal/",
		"display": "standalone",
		"dir": "rtl",
		"lang": "ar",
		"background_color": "#F4F5F2",
		"theme_color": b["primary_color"],
		"icons": [
			{"src": "/assets/construction_core/pwa/icon-192.png", "sizes": "192x192", "type": "image/png"},
			{"src": "/assets/construction_core/pwa/icon-512.png", "sizes": "512x512", "type": "image/png"},
			{
				"src": "/assets/construction_core/pwa/icon-512.png",
				"sizes": "512x512",
				"type": "image/png",
				"purpose": "maskable",
			},
		],
	}
	return Response(json.dumps(data, ensure_ascii=False), content_type="application/manifest+json")


SERVICE_WORKER = """
const CACHE = '%(version)s';
// Static assets only. Never /api, never pages with data.
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (!url.pathname.startsWith('/assets/')) return;
  e.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
        if (res.ok) cache.put(e.request, res.clone());
        return res;
      }))
    )
  );
});
"""


@frappe.whitelist(allow_guest=True)
def service_worker():
	"""Service worker served with Service-Worker-Allowed so it can control /portal/."""
	resp = Response(SERVICE_WORKER % {"version": SW_VERSION}, content_type="application/javascript")
	resp.headers["Service-Worker-Allowed"] = "/portal/"
	resp.headers["Cache-Control"] = "no-cache"
	return resp
