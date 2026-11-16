"""The only module with allow_guest=True (CLAUDE.md rule 5).

Everything here returns an explicit allowlist of fields.
"""

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, cstr, flt
from frappe.utils.html_utils import clean_html
from werkzeug.wrappers import Response

from construction_core.branding import get_branding

SW_VERSION = "cc-portal-v2"


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
const SHELL = '/portal/';
// Static assets: cache first. The portal page itself: network first, the last copy offline.
// Never /api (data is cached by the app with its own "last updated" time).
self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.add(SHELL)).catch(() => null));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (e.request.mode === 'navigate' && url.pathname.startsWith('/portal')) {
    e.respondWith(
      fetch(e.request).then((res) => {
        if (res.ok) caches.open(CACHE).then((c) => c.put(SHELL, res.clone()));
        return res;
      }).catch(() => caches.match(SHELL))
    );
    return;
  }
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
// Web Push: the push has no payload; ask the server what to show (logged-in session).
self.addEventListener('push', (e) => {
  e.waitUntil(
    fetch('/api/method/construction_core.push.latest', { credentials: 'include', headers: { Accept: 'application/json' } })
      .then((r) => r.json())
      .then((d) => {
        const n = (d && d.message) || {};
        return self.registration.showNotification(n.title || 'إشعار جديد', {
          body: '', tag: n.tag || 'cc', data: { url: n.url || '/portal/' }, dir: 'rtl', lang: 'ar',
          icon: '/assets/construction_core/pwa/icon-192.png',
        });
      })
      .catch(() => self.registration.showNotification('إشعار جديد', { data: { url: '/portal/' } }))
  );
});
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/portal/';
  e.waitUntil(self.clients.matchAll({ type: 'window' }).then((wins) => {
    for (const w of wins) { if ('focus' in w) { w.navigate(url); return w.focus(); } }
    return self.clients.openWindow(url);
  }));
});
// Background Sync (Android Chrome): wake the open portal to flush the queue.
self.addEventListener('sync', (e) => {
  if (e.tag === 'cc-queue') {
    e.waitUntil(self.clients.matchAll().then((cs) => cs.forEach((c) => c.postMessage({ type: 'cc-sync' }))));
  }
});
"""


@frappe.whitelist(allow_guest=True)
def service_worker():
	"""Service worker served with Service-Worker-Allowed so it can control /portal/."""
	resp = Response(SERVICE_WORKER % {"version": SW_VERSION}, content_type="application/javascript")
	resp.headers["Service-Worker-Allowed"] = "/portal/"
	resp.headers["Cache-Control"] = "no-cache"
	return resp


# --- Public site (phase 5) ------------------------------------------------------------
# Every function returns named fields only. Private, missing, expired and revoked
# items all raise the same NotFound.


PAGE_SIZE = 12
DESIGN_CARD_FIELDS = [
	"name",
	"slug",
	"title",
	"style",
	"area_m2",
	"bedrooms",
	"bathrooms",
	"cost_from",
	"cost_to",
	"duration_weeks",
	"cover_public",
	"modified",
]
SORTS = {
	"newest": "creation desc",
	"price_asc": "cost_from asc",
	"price_desc": "cost_from desc",
	"area": "area_m2 asc",
}


class NotFound(frappe.DoesNotExistError):
	pass


def not_found():
	raise NotFound(_("Not found"))


def _design_card(d) -> dict:
	return {
		"slug": d.slug,
		"title": d.title,
		"style": d.style,
		"area_m2": flt(d.area_m2),
		"bedrooms": cint(d.bedrooms),
		"bathrooms": cint(d.bathrooms),
		"cost_from": flt(d.cost_from),
		"cost_to": flt(d.cost_to),
		"duration_weeks": cint(d.duration_weeks),
		"cover": d.cover_public or "",
	}


@frappe.whitelist(allow_guest=True)
def list_designs(filters: str | dict | None = None, sort: str = "newest", page: int = 1) -> dict:
	f = frappe.parse_json(filters) if filters else {}
	conditions = [["published", "=", 1]]
	if f.get("area_min"):
		conditions.append(["area_m2", ">=", flt(f["area_min"])])
	if f.get("area_max"):
		conditions.append(["area_m2", "<=", flt(f["area_max"])])
	if f.get("bedrooms"):
		conditions.append(["bedrooms", "=", cint(f["bedrooms"])])
	if f.get("bathrooms"):
		conditions.append(["bathrooms", "=", cint(f["bathrooms"])])
	if f.get("style"):
		conditions.append(["style", "=", cstr(f["style"])])
	if f.get("price_max"):
		conditions.append(["cost_from", "<=", flt(f["price_max"])])
	if f.get("price_min"):
		conditions.append(["cost_to", ">=", flt(f["price_min"])])
	page = max(cint(page), 1)
	rows = frappe.get_all(
		"Design Template",
		filters=conditions,
		fields=DESIGN_CARD_FIELDS,
		order_by=SORTS.get(sort, SORTS["newest"]),
		start=(page - 1) * PAGE_SIZE,
		page_length=PAGE_SIZE,
	)
	total = frappe.db.count("Design Template", filters=conditions)
	styles = sorted(
		{s for s in frappe.get_all("Design Template", filters={"published": 1}, pluck="style") if s}
	)
	return {
		"designs": [_design_card(d) for d in rows],
		"total": total,
		"page": page,
		"pages": max(1, -(-total // PAGE_SIZE)),
		"styles": styles,
	}


@frappe.whitelist(allow_guest=True)
def get_public_design(slug: str) -> dict:
	name = frappe.db.get_value("Design Template", {"slug": cstr(slug), "published": 1}, "name")
	if not name:
		not_found()
	d = frappe.get_doc("Design Template", name)
	stages = []
	if d.phase_template:
		stages = [
			{"stage_name": r.stage_name} for r in frappe.get_doc("Phase Template", d.phase_template).stages
		]
	media = [
		{"url": m.public_file, "kind": m.kind, "caption": m.caption or ""} for m in d.media if m.public_file
	]
	return {
		**_design_card(d),
		"description": clean_html(d.description or ""),
		"media": media,
		"stages": stages,
	}


def _resolve_project(slug: str | None, token: str | None) -> str:
	from construction_core.sharing import check_share_token

	if token:
		project = cstr(slug)
		if project and check_share_token(project, token):
			return project
		not_found()
	row = frappe.db.get_value(
		"Project", {"slug": cstr(slug), "visibility": "public"}, ["name", "share_expires_at"], as_dict=True
	)
	if not slug or not row:
		not_found()
	if (
		row.share_expires_at
		and frappe.utils.get_datetime(row.share_expires_at) <= frappe.utils.now_datetime()
	):
		not_found()
	return row.name


@frappe.whitelist(allow_guest=True)
def get_public_project(slug: str | None = None, token: str | None = None) -> dict:
	"""A published project. `slug` is the public slug, or the project name when a share token is given."""
	name = _resolve_project(slug, token)
	p = frappe.get_doc("Project", name)
	out = {
		"title": p.project_name,
		"progress": flt(p.get("weighted_progress")),
		"area": p.get("area_label") or "",
	}
	if p.get("public_show_client_name") and p.customer:
		out["client_name"] = frappe.db.get_value("Customer", p.customer, "customer_name")
	if p.get("public_show_stages"):
		out["stages"] = [
			{"stage_name": s.stage_name, "status": s.status, "progress": flt(s.progress)}
			for s in frappe.get_all(
				"Project Stage",
				filters={"project": name},
				fields=["stage_name", "status", "progress"],
				order_by="sort_order asc, creation asc",
			)
		]
	updates = frappe.get_all(
		"Stage Update",
		filters={"project": name, "internal_only": 0},
		fields=["name", "text", "creation"],
		order_by="creation desc",
		limit=30,
	)
	photos_mode = p.get("public_show_photos") or "none"
	photos = []
	if photos_mode != "none":
		# Only public copies are ever exposed. "all" also means public copies only:
		# a photo needs "مناسبة للنشر" before any visitor can see it.
		for u in updates:
			for m in frappe.get_all(
				"Stage Update Media",
				filters={"parent": u.name, "parenttype": "Stage Update", "publishable": 1, "kind": "Photo"},
				fields=["public_file"],
				order_by="idx asc",
			):
				if m.public_file:
					photos.append({"url": m.public_file, "date": cstr(u.creation)[:10]})
	out["photos"] = photos
	if p.get("public_show_updates_text"):
		out["updates"] = [{"text": u.text or "", "date": cstr(u.creation)[:10]} for u in updates if u.text]
	return out


@frappe.whitelist(allow_guest=True)
def list_public_projects() -> list[dict]:
	rows = frappe.get_all(
		"Project",
		filters={"visibility": "public", "slug": ["is", "set"]},
		fields=["slug", "project_name", "weighted_progress", "area_label"],
		order_by="modified desc",
		limit=50,
	)
	return [
		{
			"slug": r.slug,
			"title": r.project_name,
			"progress": flt(r.weighted_progress),
			"area": r.area_label or "",
		}
		for r in rows
	]


EGYPT_MOBILE = r"^01[0125][0-9]{8}$"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def request_design(
	full_name: str,
	mobile: str,
	governorate: str,
	apartment_area_m2: float | None = None,
	city: str | None = None,
	design: str | None = None,
	notes: str | None = None,
	website: str | None = None,
	consent: int = 0,
) -> dict:
	""" "اطلب تنفيذ": creates a Lead. `website` is a honeypot that people never fill."""
	import re

	if website:
		# Looks like success to the bot; nothing is stored.
		return {"ok": True}
	full_name = cstr(full_name).strip()
	mobile = re.sub(r"[\s-]", "", cstr(mobile))
	if not full_name or len(full_name) > 140:
		frappe.throw(_("اكتب اسمك"))
	if not re.match(EGYPT_MOBILE, mobile):
		frappe.throw(_("رقم الموبايل لازم يكون مصري، 11 رقم يبدأ بـ 010 أو 011 أو 012 أو 015"))
	if not cstr(governorate).strip():
		frappe.throw(_("اختار المحافظة"))
	if not cint(consent):
		frappe.throw(_("لازم توافق إن المكتب يتواصل معاك"))
	design_name = None
	if design:
		design_name = frappe.db.get_value("Design Template", {"slug": cstr(design), "published": 1}, "name")
	lead = frappe.get_doc(
		{
			"doctype": "Lead",
			"lead_name": full_name,
			"first_name": full_name,
			"mobile_no": mobile,
			"city": cstr(city)[:140] or None,
			"governorate": cstr(governorate)[:140],
			"apartment_area_m2": flt(apartment_area_m2) or None,
			"design_template": design_name,
			"source": None,
		}
	)
	lead.flags.ignore_permissions = True
	lead.flags.ignore_mandatory = True
	lead.insert()
	if notes:
		lead.add_comment("Comment", text=frappe.utils.escape_html(cstr(notes)[:2000]))
	_notify_admins(lead)
	return {"ok": True}


def _notify_admins(lead):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	admins = frappe.get_all(
		"Has Role",
		filters={"role": "Construction Admin", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	admins = [a for a in admins if a not in ("Administrator", "Guest")]
	if admins:
		enqueue_create_notification(
			admins,
			{
				"type": "Alert",
				"document_type": "Lead",
				"document_name": lead.name,
				"subject": _("طلب تنفيذ جديد من {0}").format(lead.lead_name),
			},
		)


@frappe.whitelist(allow_guest=True)
def sitemap():
	"""Published designs and public projects only."""
	from frappe.utils import escape_html, get_url

	urls = [get_url("/"), get_url("/designs"), get_url("/projects")]
	urls += [
		get_url(f"/designs/{s}")
		for s in frappe.get_all("Design Template", filters={"published": 1}, pluck="slug")
	]
	urls += [
		get_url(f"/projects/{s}")
		for s in frappe.get_all(
			"Project", filters={"visibility": "public", "slug": ["is", "set"]}, pluck="slug"
		)
	]
	body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
	body += "".join(f"  <url><loc>{escape_html(u)}</loc></url>\n" for u in urls)
	body += "</urlset>\n"
	return Response(body, content_type="application/xml")


# --- Payment gateway webhook (phase 15) -----------------------------------------------


@frappe.whitelist(allow_guest=True, methods=["POST"])
def paymob_webhook():
	"""Paymob "transaction processed" callback. The HMAC is checked before anything is read or
	written; a bad signature is rejected (401) and logged without the payload's card data."""
	from construction_core.payments.gateway import get_gateway
	from construction_core.payments.online import reconcile
	from construction_core.utils import as_system

	request = frappe.request
	signature = cstr(request.args.get("hmac"))
	try:
		payload = json.loads(request.get_data(as_text=True) or "{}")
	except ValueError:
		payload = {}
	gw = get_gateway()
	if not gw.verify_webhook(payload, signature):
		frappe.log_error(
			title="Paymob webhook rejected: bad signature",
			message=f"ip={frappe.local.request_ip} has_hmac={bool(signature)}",
		)
		frappe.local.response["http_status_code"] = 401
		return {"ok": False}
	tx = gw.parse_webhook(payload)
	with as_system():
		reconcile(tx)
	return {"ok": True}
