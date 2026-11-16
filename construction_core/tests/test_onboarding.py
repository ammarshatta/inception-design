"""Phase 2: add client / engineer, stages ordering (P02-01, P02-02, P02-03, P02-05)."""

from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.password import check_password

from construction_core.api import admin
from construction_core.tests.factories import make_project, make_world, stages_of


class TestAddClient(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def new_project(self, title):
		return make_project(title, [])

	def test_client_with_email(self):
		project = self.new_project("مشروع عميل بإيميل")
		res = admin.add_client(project, "محمد علي", "01012345670", email="m.ali.test@example.com")
		self.assertEqual(res["user"], "m.ali.test@example.com")
		self.assertNotIn("temp_password", res)
		user = frappe.get_doc("User", res["user"])
		self.assertEqual(user.user_type, "Website User")
		self.assertIn("Construction Client", [r.role for r in user.roles])
		self.assertFalse(user.must_change_password)
		doc = frappe.get_doc("Project", project)
		self.assertIn(res["user"], [r.user for r in doc.users])
		self.assertEqual(doc.customer, res["customer"])
		contact = frappe.db.get_value("Contact", {"user": res["user"]}, "name")
		self.assertTrue(contact)
		links = frappe.get_all(
			"Dynamic Link", filters={"parent": contact, "link_doctype": "Customer"}, pluck="link_name"
		)
		self.assertIn(res["customer"], links)

	def test_client_without_email(self):
		project = self.new_project("مشروع عميل بيوزر")
		res = admin.add_client(project, "سارة حسن", "01112345670", username="sara.hassan")
		self.assertEqual(res["username"], "sara.hassan")
		self.assertEqual(len(res["temp_password"]), 12)
		self.assertEqual(check_password(res["user"], res["temp_password"]), res["user"])
		self.assertTrue(frappe.db.get_value("User", res["user"], "must_change_password"))
		url = urlparse(res["whatsapp_url"])
		self.assertEqual(url.netloc, "wa.me")
		self.assertEqual(url.path, "/201112345670")
		text = parse_qs(url.query)["text"][0]
		self.assertIn("sara.hassan", text)
		self.assertIn(res["temp_password"], text)
		self.assertIn("/login", text)

	def test_mobile_validation(self):
		project = self.new_project("مشروع موبايل غلط")
		for bad in ("0101234567", "01312345678", "1012345678", "abc"):
			self.assertRaises(
				frappe.ValidationError, admin.add_client, project, "اسم", bad, email="bad.mobile@example.com"
			)

	def test_username_required_without_email(self):
		project = self.new_project("مشروع بدون يوزر")
		self.assertRaises(frappe.ValidationError, admin.add_client, project, "اسم", "01212345678")

	def test_add_client_admin_only(self):
		project = self.new_project("مشروع صلاحية الإضافة")
		with self.set_user(self.w.users.eng1):
			self.assertRaises(
				frappe.PermissionError,
				admin.add_client,
				project,
				"اسم",
				"01512345678",
				email="x.y@example.com",
			)

	def test_add_engineer(self):
		project = self.new_project("مشروع إضافة مهندس")
		admin.add_engineer(project, self.w.users.eng2)
		with self.set_user(self.w.users.eng2):
			self.assertIn(project, frappe.get_list("Project", pluck="name", limit_page_length=0))
		self.assertRaises(frappe.ValidationError, admin.add_engineer, project, self.w.users.client1)


class TestStagesOrdering(IntegrationTestCase):
	def test_move_stage_and_total(self):
		project = make_project("مشروع ترتيب المراحل", [])
		names = stages_of(project)
		res = admin.move_stage(names[1], "up")
		order = [s["name"] for s in res["stages"]]
		self.assertEqual(order[0], names[1])
		self.assertEqual(order[1], names[0])
		self.assertEqual(res["total_weight"], 100)
		self.assertTrue(res["ok"])
