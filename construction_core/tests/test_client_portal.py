"""Phase 4: client portal API, approvals, notifications (P04-01..P04-07)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from construction_core.api import portal
from construction_core.tests.factories import make_milestone, make_update, make_world, stages_of

PROJECT_METHODS = [
	("client_home", {}),
	("timeline", {}),
	("gallery", {}),
	("payments", {}),
	("messages", {}),
	("send_message", {"text": "x"}),
]


class TestClientPortal(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		cls.s1 = stages_of(cls.w.p1)

	def test_every_method_rejects_other_project(self):
		with self.set_user(self.w.users.client1):
			for method, kwargs in PROJECT_METHODS:
				with self.subTest(method=method):
					self.assertRaises(
						frappe.PermissionError, getattr(portal, method), project=self.w.p2, **kwargs
					)

	def test_answer_approval_other_project_rejected(self):
		with self.set_user(self.w.users.eng2):
			msg = portal.request_approval(self.w.p2, "طلب", "تفاصيل", 100)["name"]
		with self.set_user(self.w.users.client1):
			self.assertRaises(frappe.PermissionError, portal.answer_approval, msg, "Approved")

	def test_home_shows_last_three_non_internal(self):
		stage = self.s1[0]
		names = [make_update(self.w.p1, stage, text=f"u{i}") for i in range(4)]
		internal = make_update(self.w.p1, stage, internal_only=1, text="secret")
		with self.set_user(self.w.users.client1):
			home = portal.client_home(self.w.p1)
		got = [u.name for u in home["updates"]]
		self.assertEqual(len(got), 3)
		self.assertNotIn(internal, got)
		self.assertEqual(got[0], names[-1])

	def test_internal_never_in_gallery(self):
		stage = self.s1[1]
		internal = make_update(self.w.p1, stage, internal_only=1, text="secret photo")
		doc = frappe.get_doc("Stage Update", internal)
		doc.append("media", {"file": "/private/files/x.jpg", "kind": "Photo"})
		doc.save(ignore_permissions=True)
		with self.set_user(self.w.users.client1):
			groups = portal.gallery(self.w.p1)["groups"]
		self.assertNotIn(internal, [g["update"] for g in groups])

	def test_timeline_delay(self):
		stage = frappe.get_doc("Project Stage", self.s1[5])
		stage.planned_start = add_days(nowdate(), -20)
		stage.planned_end = add_days(nowdate(), -10)
		stage.status = "Done"
		stage.actual_start = add_days(nowdate(), -20)
		stage.actual_end = add_days(nowdate(), -6)
		stage.save(ignore_permissions=True)
		with self.set_user(self.w.users.client1):
			rows = portal.timeline(self.w.p1)["stages"]
		row = next(r for r in rows if r["name"] == stage.name)
		self.assertEqual(row["delay_days"], 4)

	def test_delay_days_open_stage(self):
		self.assertEqual(
			portal.delay_days({"planned_end": add_days(nowdate(), -3), "status": "In Progress"}), 3
		)
		self.assertEqual(
			portal.delay_days({"planned_end": add_days(nowdate(), 5), "status": "In Progress"}), 0
		)
		self.assertEqual(portal.delay_days({"planned_end": None}), 0)

	def test_payments_and_next_payment(self):
		project = self.w.p1
		make_milestone(project, self.s1[6], 1000, "دفعة أ")
		due = make_milestone(project, self.s1[7], 2500, "دفعة ب")
		frappe.db.set_value("Payment Milestone", due, "status", "Due")
		with self.set_user(self.w.users.client1):
			pay = portal.payments(project)
			home = portal.client_home(project)
		self.assertGreaterEqual(pay["total"], 3500)
		self.assertEqual(home["next_payment"]["name"], due)

	def test_chat_and_approval_flow(self):
		with self.set_user(self.w.users.client1):
			sent = portal.send_message(self.w.p1, "سؤال عن السيراميك")
			self.assertTrue(sent["mine"])
			self.assertRaises(frappe.PermissionError, portal.request_approval, self.w.p1, "x", "y", 1)
		with self.set_user(self.w.users.eng1):
			msgs = portal.messages(self.w.p1)
			self.assertIn(sent["name"], [m["name"] for m in msgs])
			appr = portal.request_approval(self.w.p1, "سيراميك الريسبشن", "فرق السعر", 6000)
			self.assertRaises(frappe.PermissionError, portal.answer_approval, appr["name"], "Approved")
		with self.set_user(self.w.users.client1):
			ans = portal.answer_approval(appr["name"], "Approved")
			self.assertEqual(ans["approval_status"], "Approved")
			self.assertTrue(ans["answered_on"])
			self.assertRaises(frappe.PermissionError, portal.answer_approval, appr["name"], "Question")
		# Admin through the API: still locked
		self.assertRaises(frappe.PermissionError, portal.answer_approval, appr["name"], "Question")

	def test_message_with_photo(self):
		with self.set_user(self.w.users.client1):
			f = frappe.get_doc(
				{"doctype": "File", "file_name": "chat.jpg", "content": b"\xff\xd8\xff\xd9", "is_private": 1}
			).insert(ignore_permissions=True)
			msg = portal.send_message(self.w.p1, "", f.file_url)
		self.assertEqual(frappe.db.get_value("File", f.name, "attached_to_name"), msg["name"])


class TestNotifications(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def logs(self, user, doctype, name):
		return frappe.get_all(
			"Notification Log", filters={"for_user": user, "document_type": doctype, "document_name": name}
		)

	def test_update_notifies_client_internal_does_not(self):
		stage = stages_of(self.w.p1)[0]
		with self.set_user(self.w.users.eng1):
			public = frappe.get_doc(
				{"doctype": "Stage Update", "project": self.w.p1, "project_stage": stage, "text": "عام"}
			).insert()
			internal = frappe.get_doc(
				{
					"doctype": "Stage Update",
					"project": self.w.p1,
					"project_stage": stage,
					"text": "داخلي",
					"internal_only": 1,
				}
			).insert()
		self.assertTrue(self.logs(self.w.users.client1, "Stage Update", public.name))
		self.assertFalse(self.logs(self.w.users.client1, "Stage Update", internal.name))
		self.assertFalse(self.logs(self.w.users.client2, "Stage Update", public.name))

	def test_approval_notifies_client(self):
		with self.set_user(self.w.users.eng1):
			appr = portal.request_approval(self.w.p1, "طلب موافقة", "", None)
		self.assertTrue(self.logs(self.w.users.client1, "Project Message", appr["name"]))

	def test_due_milestone_notifies_client(self):
		stage = stages_of(self.w.p1)[2]
		m = make_milestone(self.w.p1, stage, 700, "دفعة الكهرباء")
		doc = frappe.get_doc("Project Stage", stage)
		doc.status = "Done"
		doc.save(ignore_permissions=True)
		self.assertTrue(self.logs(self.w.users.client1, "Payment Milestone", m))
		self.assertTrue(self.logs(self.w.users.client1, "Project Stage", stage))
