"""Creates the user for the Playwright portal test (CI and local). Test sites only."""

import frappe
from frappe.utils.password import update_password


def create_e2e_user(email: str, password: str, first_name: str = "عميل", last_name: str = "التجربة"):
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		user.add_roles("Construction Client")
	update_password(email, password)
	frappe.db.commit()
	return frappe.db.get_value("User", email, "full_name")
