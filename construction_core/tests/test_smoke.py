import frappe
from frappe.tests import IntegrationTestCase


class TestSmoke(IntegrationTestCase):
	def test_app_installed(self):
		self.assertIn("construction_core", frappe.get_installed_apps())

	def test_roles_exist(self):
		for role in ("Construction Admin", "Construction Engineer", "Construction Client"):
			self.assertTrue(frappe.db.exists("Role", role), role)

	def test_portal_route_rule(self):
		rules = frappe.get_hooks("website_route_rules", app_name="construction_core")
		self.assertIn({"from_route": "/portal/<path:app_path>", "to_route": "portal"}, rules)
