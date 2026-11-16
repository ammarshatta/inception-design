"""Login rules (phase 2, tasks 4–6).

- Forced password change while `User.must_change_password = 1` (story P02-04).
- No self-registration through Google/Facebook (story P02-07).
"""

from urllib.parse import quote

import frappe
from frappe import _
from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect

UPDATE_PASSWORD_PATH = "/update-password"

# Paths a user with a temporary password may still reach.
ALLOWED_PREFIXES = (
	"/assets/",
	"/files/",
	"/socket.io",
	UPDATE_PASSWORD_PATH,
	"/login",
	"/website_script.js",
	"/favicon",
)
ALLOWED_METHODS = frozenset(
	{
		"login",
		"logout",
		"frappe.auth.get_logged_user",
		"frappe.core.doctype.user.user.update_password",
		"frappe.core.doctype.user.user.test_password_strength",
		"frappe.website.doctype.website_settings.website_settings.get_auto_account_deletion",
	}
)

UNREGISTERED_MESSAGE = "الحساب ده مش مسجّل، كلّم المكتب"


STATIC_EXTENSIONS = (".js", ".css", ".map", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".ttf")


def is_allowed_while_changing_password(path: str) -> bool:
	path = path or "/"
	if path.startswith(ALLOWED_PREFIXES):
		return True
	if not path.startswith("/api/") and path.lower().endswith(STATIC_EXTENSIONS):
		return True  # static files the change-password page loads (never data)
	if path.startswith("/api/method/"):
		method = path[len("/api/method/") :].split("/")[0]
		return method in ALLOWED_METHODS
	if path.startswith("/api/v2/method/"):
		method = path[len("/api/v2/method/") :].split("/")[0]
		return method in ALLOWED_METHODS
	return False


def must_change_password(user: str | None) -> bool:
	if not user or user in ("Guest", "Administrator"):
		return False
	return bool(frappe.db.get_value("User", user, "must_change_password"))


def force_password_change():
	"""before_request hook."""
	request = getattr(frappe.local, "request", None)
	if request is None:
		return
	user = getattr(getattr(frappe.local, "session", None), "user", None)
	if not must_change_password(user):
		return
	if is_allowed_while_changing_password(request.path):
		return
	if request.path.startswith("/api/"):
		frappe.throw(_("Change your temporary password first"), frappe.PermissionError)
	raise HTTPException(response=redirect(UPDATE_PASSWORD_PATH + "?redirect-to=" + quote(request.path)))


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
	new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
):
	"""Wraps Frappe's update_password and clears `must_change_password` when it succeeds."""
	from frappe.core.doctype.user.user import update_password as frappe_update_password

	result = frappe_update_password(
		new_password=new_password, logout_all_sessions=logout_all_sessions, key=key, old_password=old_password
	)
	failed = frappe.local.response.get("http_status_code") == 410
	user = frappe.session.user
	if not failed and user not in ("Guest", None):
		frappe.db.set_value("User", user, "must_change_password", 0, update_modified=False)
		if must_redirect_to_portal(user):
			return "/portal"
	return result


def must_redirect_to_portal(user: str) -> bool:
	return (
		"Construction Client" in frappe.get_roles(user)
		and frappe.db.get_value("User", user, "user_type") == "Website User"
	)


# --- Social login ----------------------------------------------------------------------


def user_before_insert(doc, method=None):
	"""Last line of defence: no user is ever created during an OAuth login."""
	if frappe.flags.in_oauth_login:
		frappe.throw(UNREGISTERED_MESSAGE, frappe.PermissionError)


def _arabic_refusal():
	"""Replace Frappe's English 'Signup is Disabled' page with our Arabic message."""
	if frappe.local.response.get("http_status_code") == 403 and frappe.local.response.get("type") == "page":
		frappe.respond_as_web_page(
			UNREGISTERED_MESSAGE,
			UNREGISTERED_MESSAGE,
			success=False,
			http_status_code=403,
		)


def _guarded(provider_fn, *args, **kwargs):
	frappe.flags.in_oauth_login = True
	try:
		provider_fn(*args, **kwargs)
	except frappe.PermissionError as e:
		if str(e) != UNREGISTERED_MESSAGE:
			raise
		frappe.db.rollback()
		frappe.local.response["http_status_code"] = 403
		frappe.local.response["type"] = "page"
	finally:
		frappe.flags.in_oauth_login = False
	_arabic_refusal()


@frappe.whitelist(allow_guest=True)
def login_via_google(code: str, state: str):
	from frappe.integrations.oauth2_logins import login_via_google as original

	_guarded(original, code, state)


@frappe.whitelist(allow_guest=True)
def login_via_facebook(code: str, state: str):
	from frappe.integrations.oauth2_logins import login_via_facebook as original

	_guarded(original, code, state)
