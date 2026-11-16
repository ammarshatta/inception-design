"""Project-level permissions (story P01-01, P01-02; phase 1 required tests)."""

import frappe
from frappe.tests import IntegrationTestCase

from construction_core.permissions import assert_project_access
from construction_core.tests.factories import (
	make_message,
	make_milestone,
	make_update,
	make_world,
	stages_of,
)


class TestProjectPermissions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		cls.s1 = stages_of(cls.w.p1)[0]
		cls.s2 = stages_of(cls.w.p2)[0]
		cls.u1_public = make_update(cls.w.p1, cls.s1, internal_only=0, text="public")
		cls.u1_internal = make_update(cls.w.p1, cls.s1, internal_only=1, text="internal")
		cls.u2 = make_update(cls.w.p2, cls.s2)
		cls.m2 = make_milestone(cls.w.p2, cls.s2)
		cls.msg2 = make_message(cls.w.p2, text="hello")

	def assert_hidden(self, user, doctype, name, project_field="project", project=None):
		with self.set_user(user):
			self.assertRaises(frappe.PermissionError, frappe.get_doc, doctype, name)
			names = frappe.get_list(doctype, pluck="name", limit_page_length=0)
			self.assertNotIn(name, names)

	def assert_visible(self, user, doctype, name):
		with self.set_user(user):
			doc = frappe.get_doc(doctype, name)
			doc.check_permission("read")
			self.assertIn(name, frappe.get_list(doctype, pluck="name", limit_page_length=0))

	# Engineer outside the project ------------------------------------------------------

	def test_engineer_cannot_read_other_project(self):
		self.assert_hidden(self.w.users.eng1, "Project", self.w.p2)

	def test_engineer_reads_own_project(self):
		self.assert_visible(self.w.users.eng1, "Project", self.w.p1)

	def test_engineer_cannot_read_other_project_records(self):
		eng = self.w.users.eng1
		self.assert_hidden(eng, "Project Stage", self.s2)
		self.assert_hidden(eng, "Stage Update", self.u2)
		self.assert_hidden(eng, "Payment Milestone", self.m2)
		self.assert_hidden(eng, "Project Message", self.msg2)

	def test_engineer_sees_internal_updates_on_own_project(self):
		self.assert_visible(self.w.users.eng1, "Stage Update", self.u1_internal)

	# Client on another client's project -------------------------------------------------

	def test_client_cannot_read_other_clients_project(self):
		self.assert_hidden(self.w.users.client1, "Project", self.w.p2)

	def test_client_cannot_read_other_clients_records(self):
		client = self.w.users.client1
		self.assert_hidden(client, "Project Stage", self.s2)
		self.assert_hidden(client, "Stage Update", self.u2)
		self.assert_hidden(client, "Payment Milestone", self.m2)
		self.assert_hidden(client, "Project Message", self.msg2)

	def test_client_reads_own_project_and_public_update(self):
		self.assert_visible(self.w.users.client1, "Project", self.w.p1)
		self.assert_visible(self.w.users.client1, "Stage Update", self.u1_public)

	# internal_only ---------------------------------------------------------------------

	def test_client_cannot_read_internal_update(self):
		self.assert_hidden(self.w.users.client1, "Stage Update", self.u1_internal)

	# Messages --------------------------------------------------------------------------

	def test_client_can_send_text_message(self):
		with self.set_user(self.w.users.client1):
			doc = frappe.get_doc(
				{"doctype": "Project Message", "project": self.w.p1, "kind": "Text", "text": "سؤال"}
			)
			doc.insert()
			self.assertTrue(doc.name)

	def test_client_cannot_create_approval(self):
		with self.set_user(self.w.users.client1):
			doc = frappe.get_doc(
				{
					"doctype": "Project Message",
					"project": self.w.p1,
					"kind": "Approval",
					"approval_title": "x",
				}
			)
			self.assertRaises(frappe.PermissionError, doc.insert)

	def test_client_cannot_message_other_project(self):
		with self.set_user(self.w.users.client1):
			doc = frappe.get_doc(
				{"doctype": "Project Message", "project": self.w.p2, "kind": "Text", "text": "x"}
			)
			self.assertRaises(frappe.PermissionError, doc.insert)

	# Helper ----------------------------------------------------------------------------

	def test_assert_project_access(self):
		with self.set_user(self.w.users.eng1):
			assert_project_access(self.w.p1)
			self.assertRaises(frappe.PermissionError, assert_project_access, self.w.p2)

	def test_admin_sees_everything(self):
		self.assert_visible(self.w.users.admin, "Project", self.w.p2)
		self.assert_visible(self.w.users.admin, "Stage Update", self.u1_internal)
