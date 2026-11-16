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


def create_temp_password_client(username: str = "e2e.temp") -> dict:
	"""A project plus a client added without email (temporary password), for Playwright."""
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	from construction_core.api.admin import add_client
	from construction_core.tests.factories import make_project

	existing = frappe.db.get_value("User", {"username": username}, "name")
	if existing:
		frappe.delete_doc("User", existing, ignore_permissions=True, force=True)
	project = make_project("مشروع تجربة كلمة السر المؤقتة", [])
	res = add_client(project, "عميل مؤقت", "01098765432", username=username)
	frappe.db.commit()
	return {"username": res["username"], "password": res["temp_password"]}
