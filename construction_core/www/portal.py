"""Serves the Vue portal (frontend/) at /portal. Login is required."""

from urllib.parse import quote

import frappe
from frappe import _

from construction_core.branding import get_branding, get_feature_flags

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		path = frappe.request.path if getattr(frappe, "request", None) else "/portal"
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(path)
		raise frappe.Redirect

	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # persist the csrf token for this session

	user = frappe.get_cached_doc("User", frappe.session.user)
	context.no_cache = 1
	context.boot = {
		"csrf_token": csrf_token,
		"site_name": frappe.local.site,
		"session_user": frappe.session.user,
		"user_full_name": user.full_name or user.first_name or frappe.session.user,
		"lang": "ar",
		"branding": get_branding(),
		"features": get_feature_flags(),
	}
	context.title = _("Portal")
	return context
