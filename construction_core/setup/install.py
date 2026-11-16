"""Install and migrate hooks: roles' rights on ERPNext's Project, and test bootstrap."""

import frappe
from frappe.permissions import add_permission, update_permission_property

# Rights our roles need on ERPNext DocTypes. Our own DocTypes carry their
# permissions in their JSON. add_permission copies ERPNext's standard rules into
# Custom DocPerm first, so existing roles keep their access.
ERPNEXT_DOCPERMS = {
	"Project": {
		"Construction Admin": (
			"read",
			"write",
			"create",
			"delete",
			"report",
			"export",
			"print",
			"email",
			"share",
		),
		"Construction Engineer": ("read", "select"),
		"Construction Client": ("read", "select"),
	},
}


def after_install():
	ensure_permissions()
	apply_login_settings()


def after_migrate():
	ensure_permissions()
	apply_login_settings()


def apply_login_settings():
	"""Phase 2, task 5: no self-signup, username login, lockout after 5 failed attempts."""
	frappe.db.set_single_value("Website Settings", "disable_signup", 1)
	frappe.db.set_single_value(
		"System Settings",
		{
			"allow_login_using_user_name": 1,
			"allow_consecutive_login_attempts": 5,
			"allow_login_after_fail": 900,
		},
	)
	# A Social Login Key set to "Allow" would override disable_signup for that provider.
	for key in frappe.get_all("Social Login Key", filters={"sign_ups": "Allow"}, pluck="name"):
		frappe.db.set_value("Social Login Key", key, "sign_ups", "Deny")


def ensure_permissions():
	for doctype, roles in ERPNEXT_DOCPERMS.items():
		for role, ptypes in roles.items():
			if not frappe.db.exists("Role", role):
				continue
			if not frappe.db.exists(
				"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
			):
				add_permission(doctype, role, 0)
			for ptype in ptypes:
				update_permission_property(doctype, role, 0, ptype, 1, validate=False)
	frappe.clear_cache()


def before_tests():
	"""CI sites have no company. Run the setup wizard once, non-interactively."""
	frappe.clear_cache()
	if frappe.is_setup_complete():
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
	from frappe.utils import getdate

	year = getdate().year
	setup_complete(
		{
			"currency": "EGP",
			"full_name": "Test Admin",
			"company_name": "Construction Test Co",
			"timezone": "Africa/Cairo",
			"company_abbr": "CTC",
			"industry": "Construction",
			"country": "Egypt",
			"fy_start_date": f"{year}-01-01",
			"fy_end_date": f"{year}-12-31",
			"language": "english",
			"company_tagline": "Testing",
			"email": "test-admin@example.com",
			"password": "test-admin-password",
			"chart_of_accounts": "Standard",
		}
	)
	frappe.db.commit()
