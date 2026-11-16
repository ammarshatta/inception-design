"""Answered approvals are locked for everyone (P01-06)."""

import frappe
import frappe.client
from frappe.tests import IntegrationTestCase

from construction_core.tests.factories import make_message, make_world


class TestApprovals(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def new_approval(self):
		return make_message(
			self.w.p1,
			kind="Approval",
			approval_title="سيراميك الريسبشن",
			approval_detail="فرق 6000",
			approval_amount=6000,
		)

	def test_new_approval_is_pending(self):
		name = self.new_approval()
		self.assertEqual(frappe.db.get_value("Project Message", name, "approval_status"), "Pending")

	def test_client_answers_then_locked_even_for_administrator(self):
		name = self.new_approval()
		with self.set_user(self.w.users.client1):
			doc = frappe.get_doc("Project Message", name)
			doc.approval_status = "Approved"
			doc.save()
			self.assertEqual(doc.answered_by, self.w.users.client1)
			self.assertTrue(doc.answered_on)

		self.assertEqual(frappe.session.user, "Administrator")
		doc = frappe.get_doc("Project Message", name)
		doc.approval_amount = 1
		self.assertRaises(frappe.PermissionError, doc.save)

		doc = frappe.get_doc("Project Message", name)
		doc.approval_status = "Question"
		self.assertRaises(frappe.PermissionError, doc.save)
		self.assertRaises(frappe.PermissionError, frappe.delete_doc, "Project Message", name)

	def test_client_cannot_change_other_fields(self):
		name = self.new_approval()
		with self.set_user(self.w.users.client1):
			doc = frappe.get_doc("Project Message", name)
			doc.approval_amount = 1
			self.assertRaises(frappe.PermissionError, doc.save)

	def test_other_client_cannot_answer(self):
		name = self.new_approval()
		with self.set_user(self.w.users.client2):
			self.assertRaises(frappe.PermissionError, frappe.client.get, "Project Message", name)
			doc = frappe.get_doc("Project Message", name)
			doc.approval_status = "Approved"
			self.assertRaises(frappe.PermissionError, doc.save)
