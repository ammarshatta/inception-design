"""Web Push for the portal PWA (phase 16).

- VAPID keys come from site_config.json (`vapid_public_key`, `vapid_private_key`), never git.
  `bench --site <site> execute construction_core.push.generate_vapid_keys` prints a new pair.
- Pushes carry **no payload**: the phone is only woken up, and the service worker then asks
  `latest` for the newest notification over the logged-in session. So no message text ever
  passes through the browser vendor's push service, and no payload encryption is needed.
- Categories can be muted per user: message, approval, selection, payment, schedule, update.
"""

import base64
import hashlib
import json
import time
from urllib.parse import urlparse

import frappe
import requests
from frappe import _

CATEGORIES = ("message", "approval", "selection", "payment", "schedule", "update")
DOCTYPE_CATEGORY = {
	"Project Message": "message",
	"Signature Request": "approval",
	"Change Order": "approval",
	"Project Selection": "selection",
	"Payment Milestone": "payment",
	"Online Payment": "payment",
	"Task": "schedule",
	"Crew Assignment": "schedule",
	"Stage Update": "update",
	"Project Stage": "update",
}


def _b64url(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
	return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def generate_vapid_keys() -> dict:
	from cryptography.hazmat.primitives import serialization
	from cryptography.hazmat.primitives.asymmetric import ec

	key = ec.generate_private_key(ec.SECP256R1())
	private = key.private_numbers().private_value.to_bytes(32, "big")
	public = key.public_key().public_bytes(
		serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
	)
	return {"vapid_private_key": _b64url(private), "vapid_public_key": _b64url(public)}


def _vapid_header(endpoint: str) -> dict:
	from cryptography.hazmat.primitives import hashes
	from cryptography.hazmat.primitives.asymmetric import ec
	from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

	private = frappe.conf.get("vapid_private_key")
	public = frappe.conf.get("vapid_public_key")
	if not (private and public):
		raise RuntimeError("VAPID keys are not set in site_config.json")
	u = urlparse(endpoint)
	claims = {
		"aud": f"{u.scheme}://{u.netloc}",
		"exp": int(time.time()) + 12 * 3600,
		"sub": frappe.conf.get("vapid_subject") or "mailto:no-reply@example.invalid",
	}
	header = _b64url(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
	body = _b64url(json.dumps(claims, separators=(",", ":")).encode())
	key = ec.derive_private_key(int.from_bytes(_b64url_decode(private), "big"), ec.SECP256R1())
	der = key.sign(f"{header}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
	r, s = decode_dss_signature(der)
	sig = _b64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
	return {"Authorization": f"vapid t={header}.{body}.{sig}, k={public}"}


def muted(user: str) -> set[str]:
	value = frappe.db.get_value("User", user, "push_muted_categories") or ""
	return {c for c in value.split(",") if c}


def recipients(users: list[str], category: str) -> list[str]:
	return [u for u in users if u and category not in muted(u)]


def _send_one(sub) -> bool:
	try:
		r = requests.post(
			sub.endpoint,
			headers={**_vapid_header(sub.endpoint), "TTL": "86400", "Urgency": "normal"},
			timeout=10,
		)
	except requests.RequestException:
		frappe.db.set_value("Push Subscription", sub.name, "failures", (sub.failures or 0) + 1)
		return False
	if r.status_code in (404, 410):  # the browser dropped the subscription
		frappe.delete_doc("Push Subscription", sub.name, ignore_permissions=True, force=True)
		return False
	ok = r.status_code < 300
	frappe.db.set_value(
		"Push Subscription",
		sub.name,
		{"last_sent": frappe.utils.now_datetime(), "failures": 0 if ok else (sub.failures or 0) + 1},
	)
	return ok


def send(users: list[str], category: str) -> int:
	if not frappe.conf.get("vapid_private_key"):
		return 0
	sent = 0
	for user in recipients(users, category):
		for sub in frappe.get_all(
			"Push Subscription", filters={"user": user}, fields=["name", "endpoint", "failures"]
		):
			sent += _send_one(sub)
	return sent


def category_of(doctype: str, name: str | None = None) -> str:
	if (
		doctype == "Project Message"
		and name
		and frappe.db.get_value("Project Message", name, "kind") == "Approval"
	):
		return "approval"
	return DOCTYPE_CATEGORY.get(doctype, "update")


def notify(users: list[str], doctype: str, name: str | None = None):
	"""Called by notifications._notify after the in-app notification is created."""
	category = category_of(doctype, name)
	targets = recipients(users, category)
	if not targets or not frappe.conf.get("vapid_private_key"):
		return
	frappe.enqueue(
		"construction_core.push.send",
		users=targets,
		category=category,
		queue="short",
		enqueue_after_commit=True,
		now=frappe.flags.in_test,
	)


# --- Portal API -----------------------------------------------------------------------


def _require_user():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)


@frappe.whitelist()
def settings() -> dict:
	_require_user()
	return {
		"public_key": frappe.conf.get("vapid_public_key"),
		"categories": list(CATEGORIES),
		"muted": sorted(muted(frappe.session.user)),
		"devices": frappe.db.count("Push Subscription", {"user": frappe.session.user}),
	}


@frappe.whitelist(methods=["POST"])
def set_muted(categories: list | str) -> list[str]:
	_require_user()
	categories = frappe.parse_json(categories) if isinstance(categories, str) else categories
	clean = sorted({c for c in categories or [] if c in CATEGORIES})
	frappe.db.set_value("User", frappe.session.user, "push_muted_categories", ",".join(clean))
	return clean


@frappe.whitelist(methods=["POST"])
def subscribe(subscription: dict | str, device: str | None = None) -> str:
	"""Store this browser's push subscription for the current user (one row per endpoint)."""
	_require_user()
	sub = frappe.parse_json(subscription) if isinstance(subscription, str) else subscription
	endpoint = (sub or {}).get("endpoint") or ""
	if not endpoint.startswith("https://") or len(endpoint) > 1000:
		frappe.throw(_("Invalid subscription"))
	h = hashlib.sha256(endpoint.encode()).hexdigest()
	existing = frappe.db.get_value("Push Subscription", {"endpoint_hash": h}, "name")
	if existing:
		frappe.db.set_value(
			"Push Subscription", existing, {"user": frappe.session.user, "device": (device or "")[:140]}
		)
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Push Subscription",
				"user": frappe.session.user,
				"endpoint": endpoint,
				"endpoint_hash": h,
				"device": (device or "")[:140],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


@frappe.whitelist(methods=["POST"])
def unsubscribe(endpoint: str) -> None:
	_require_user()
	h = hashlib.sha256((endpoint or "").encode()).hexdigest()
	name = frappe.db.get_value("Push Subscription", {"endpoint_hash": h, "user": frappe.session.user}, "name")
	if name:
		frappe.delete_doc("Push Subscription", name, ignore_permissions=True, force=True)


PORTAL_URLS = {
	"Project Message": lambda d: f"/portal/c/{frappe.db.get_value('Project Message', d, 'project')}/chat",
	"Signature Request": lambda d: f"/portal/sign/{d}",
	"Stage Update": lambda d: f"/portal/stages/{frappe.db.get_value('Stage Update', d, 'project_stage')}",
	"Project Stage": lambda d: f"/portal/stages/{d}",
	"Payment Milestone": lambda d: (
		f"/portal/c/{frappe.db.get_value('Payment Milestone', d, 'project')}/payments"
	),
	"Project Selection": lambda d: (
		f"/portal/c/{frappe.db.get_value('Project Selection', d, 'project')}/selections"
	),
	"Change Order": lambda d: f"/portal/c/{frappe.db.get_value('Change Order', d, 'project')}/changes",
}


@frappe.whitelist()
def latest() -> dict:
	"""The newest unread notification, for the service worker to show after a push."""
	_require_user()
	rows = frappe.get_all(
		"Notification Log",
		filters={"for_user": frappe.session.user, "read": 0},
		fields=["name", "subject", "document_type", "document_name"],
		order_by="creation desc",
		limit=1,
	)
	if not rows:
		return {}
	n = rows[0]
	url = "/portal/"
	if n.document_type in PORTAL_URLS and n.document_name:
		try:
			url = PORTAL_URLS[n.document_type](n.document_name)
		except Exception:
			url = "/portal/"
	from frappe.utils import strip_html

	return {"title": strip_html(n.subject or "")[:120], "url": url, "tag": n.name}
