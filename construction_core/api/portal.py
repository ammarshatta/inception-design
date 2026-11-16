"""Portal API (login required). Every method that takes a project calls
`assert_project_access` first (CLAUDE.md rule 5)."""

import frappe

from construction_core.branding import get_branding, get_feature_flags
from construction_core.permissions import (
	CLIENT_ROLE,
	ENGINEER_ROLE,
	has_full_access,
)


@frappe.whitelist()
def get_me() -> dict:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	doc = frappe.get_cached_doc("User", user)
	roles = set(frappe.get_roles(user))
	return {
		"user": user,
		"full_name": doc.full_name or doc.first_name or user,
		"roles": {
			"admin": has_full_access(user),
			"engineer": ENGINEER_ROLE in roles,
			"client": CLIENT_ROLE in roles,
		},
		"branding": get_branding(),
		"features": get_feature_flags(),
	}
