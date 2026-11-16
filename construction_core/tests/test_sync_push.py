"""Phase 16: idempotent offline sync, checklist conflict rule, push categories and VAPID."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, now_datetime

from construction_core import push, sync
from construction_core.tests.factories import make_world, stages_of


class TestSync(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def test_same_uuid_twice_creates_one_update(self):
		stage = stages_of(self.w.p1)[0]
		payload = {"project": self.w.p1, "stage": stage, "text": "تحديث من غير نت"}
		with self.set_user(self.w.users.eng1):
			first = sync.apply("uuid-update-1", "create_update", payload, str(now_datetime()))
			# the browser was closed before it saw the answer, and sends again
			second = sync.apply("uuid-update-1", "create_update", json.dumps(payload), str(now_datetime()))
		self.assertEqual(first["status"], "done")
		self.assertEqual(first["result"]["name"], second["result"]["name"])
		self.assertTrue(second["repeat"])
		self.assertEqual(frappe.db.count("Stage Update", {"text": "تحديث من غير نت"}), 1)
		# another user cannot replay someone else's UUID
		with self.set_user(self.w.users.eng2):
			self.assertRaises(frappe.PermissionError, sync.apply, "uuid-update-1", "create_update", payload)

	def test_permissions_still_apply(self):
		stage = stages_of(self.w.p1)[0]
		with self.set_user(self.w.users.eng2):
			self.assertRaises(
				frappe.PermissionError,
				sync.apply,
				"uuid-other-project",
				"create_update",
				{"project": self.w.p1, "stage": stage, "text": "x"},
			)
		self.assertFalse(frappe.db.exists("Sync Receipt", "uuid-other-project"))

	def test_checklist_server_wins_when_newer(self):
		stage = frappe.get_doc("Project Stage", stages_of(self.w.p1)[2])
		row = stage.checklist[0]
		phone_time = add_to_date(now_datetime(), minutes=-30)
		# someone ticked it on the server 10 minutes ago, the phone unticked it 30 minutes ago
		with self.set_user(self.w.users.eng1):
			from construction_core.api import portal

			portal.toggle_checklist_item(stage.name, row.name, 1)
			res = sync.apply(
				"uuid-tick-old", "tick", {"stage": stage.name, "row": row.name, "done": 0}, str(phone_time)
			)
			self.assertEqual(res["status"], "rejected")
			self.assertIn("السيستم", res["reason"])
			self.assertEqual(frappe.db.get_value("Stage Checklist Item", row.name, "done"), 1)
			# a newer tick from the phone is applied
			res = sync.apply(
				"uuid-tick-new",
				"tick",
				{"stage": stage.name, "row": stage.checklist[1].name, "done": 1},
				str(now_datetime()),
			)
			self.assertEqual(res["status"], "done")

	def test_clock_keeps_phone_time_and_rejects_very_old(self):
		frappe.db.set_single_value("Inceptiondesign Settings", "enable_gps_clock_in", 1)
		with self.set_user(self.w.users.eng1):
			from construction_core import sitelog

			sitelog.accept_consent(sitelog.consent()["version"])
			at = add_to_date(now_datetime(), hours=-3)
			res = sync.apply(
				"uuid-clock",
				"clock",
				{"project": self.w.p1, "event": "In", "workers": [{"worker": "عامل"}]},
				str(at),
			)
			self.assertEqual(
				str(frappe.db.get_value("Clock Event", res["result"]["names"][0], "at"))[:16], str(at)[:16]
			)
			old = sync.apply(
				"uuid-clock-old",
				"clock",
				{"project": self.w.p1, "event": "In", "workers": [{"worker": "عامل"}]},
				str(add_days(now_datetime(), -30)),
			)
			self.assertEqual(old["status"], "rejected")


class TestPush(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def test_muted_category_gets_no_push(self):
		u = self.w.users.client1
		with self.set_user(u):
			self.assertEqual(push.set_muted(["payment", "nonsense"]), ["payment"])
			push.subscribe({"endpoint": "https://push.example.test/abc", "keys": {}}, "Android")
		self.assertEqual(push.recipients([u, self.w.users.eng1], "payment"), [self.w.users.eng1])
		self.assertEqual(push.recipients([u], "message"), [u])
		keys = push.generate_vapid_keys()
		with patch.dict(frappe.conf, keys), patch("construction_core.push.requests.post") as post:
			post.return_value.status_code = 201
			self.assertEqual(push.send([u], "payment"), 0)
			post.assert_not_called()
			self.assertEqual(push.send([u], "message"), 1)
			headers = post.call_args.kwargs["headers"]
			self.assertTrue(headers["Authorization"].startswith("vapid t="))
			self.assertIn(keys["vapid_public_key"], headers["Authorization"])
			self.assertNotIn("data", post.call_args.kwargs, "no payload is ever sent")

	def test_gone_subscription_is_removed(self):
		u = self.w.users.eng1
		with self.set_user(u):
			name = push.subscribe({"endpoint": "https://push.example.test/gone"})
		with (
			patch.dict(frappe.conf, push.generate_vapid_keys()),
			patch("construction_core.push.requests.post") as post,
		):
			post.return_value.status_code = 410
			push.send([u], "message")
		self.assertFalse(frappe.db.exists("Push Subscription", name))

	def test_categories(self):
		self.assertEqual(push.category_of("Payment Milestone"), "payment")
		self.assertEqual(push.category_of("Signature Request"), "approval")
		self.assertEqual(push.category_of("Task"), "schedule")
