"""Phase 12: haversine and geofence, consent, pairing, timesheets and costing, client view."""

from datetime import datetime

import frappe
import frappe.client
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate

from construction_core import sitelog
from construction_core.tests.factories import make_world

SITE = (30.0080, 31.4300)  # a point in New Cairo


def employee(name: str) -> str:
	existing = frappe.db.get_value("Employee", {"first_name": name}, "name")
	if existing:
		return existing
	gender = (
		frappe.db.get_value("Gender", {}, "name")
		or frappe.get_doc({"doctype": "Gender", "gender": "Male"}).insert().name
	)
	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": name,
				"gender": gender,
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2024-01-01",
				"company": frappe.db.get_value("Company", {}, "name"),
				"status": "Active",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestGeo(IntegrationTestCase):
	def test_haversine_inside_edge_outside(self):
		# about 0.001° latitude ≈ 111 m
		d_in = sitelog.haversine_m(*SITE, SITE[0] + 0.0009, SITE[1])
		d_edge = sitelog.haversine_m(*SITE, SITE[0] + 0.001349, SITE[1])
		d_out = sitelog.haversine_m(*SITE, SITE[0] + 0.002, SITE[1])
		self.assertTrue(sitelog.inside_geofence(d_in, 150))
		self.assertAlmostEqual(d_edge, 150, delta=0.5)
		self.assertTrue(sitelog.inside_geofence(min(d_edge, 150), 150))
		self.assertFalse(sitelog.inside_geofence(d_out, 150))
		self.assertAlmostEqual(sitelog.haversine_m(30, 31, 30, 31), 0)

	def test_pairing_with_missing_out(self):
		ev = [
			{"name": "a", "event": "In", "at": datetime(2026, 12, 1, 8, 0)},
			{"name": "b", "event": "Out", "at": datetime(2026, 12, 1, 12, 30)},
			{"name": "c", "event": "In", "at": datetime(2026, 12, 1, 13, 0)},
		]
		pairs, unpaired = sitelog.pair_events(ev)
		self.assertEqual([p[2] for p in pairs], [4.5])
		self.assertEqual([u["name"] for u in unpaired], ["c"])


class TestClockAndTimesheets(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		frappe.db.set_single_value("Inceptiondesign Settings", "enable_gps_clock_in", 1)
		frappe.db.set_value(
			"Project", cls.w.p1, {"site_latitude": SITE[0], "site_longitude": SITE[1], "site_radius_m": 150}
		)

	def test_clock_requires_consent_and_stores_version(self):
		with self.set_user(self.w.users.eng1):
			frappe.db.set_value("User", self.w.users.eng1, "clock_consent_version", None)
			self.assertRaises(
				frappe.PermissionError,
				sitelog.clock,
				self.w.p1,
				"In",
				[{"worker": "عم سعيد"}],
				SITE[0],
				SITE[1],
			)
			version = sitelog.consent()["version"]
			sitelog.accept_consent(version)
			names = sitelog.clock(self.w.p1, "In", [{"worker": "عم سعيد"}], SITE[0] + 0.0005, SITE[1], 10)
			far = sitelog.clock(self.w.p1, "In", [{"worker": "رضا"}], SITE[0] + 0.01, SITE[1], 10)
			nogps = sitelog.clock(self.w.p1, "In", [{"worker": "حسن"}])
		e = frappe.get_doc("Clock Event", names[0])
		self.assertEqual(e.consent_version, version)
		self.assertTrue(e.inside_geofence)
		self.assertFalse(e.needs_approval)
		f = frappe.get_doc("Clock Event", far[0])
		self.assertTrue(f.needs_approval)
		self.assertFalse(f.inside_geofence)
		n = frappe.get_doc("Clock Event", nogps[0])
		self.assertTrue(n.location_missing)
		self.assertTrue(n.needs_approval)

	def test_client_cannot_clock_or_read_logs(self):
		with self.set_user(self.w.users.client1):
			self.assertRaises(frappe.PermissionError, sitelog.clock, self.w.p1, "In", [{"worker": "x"}])
			self.assertRaises(frappe.PermissionError, sitelog.get_daily_log, self.w.p1)

	def test_timesheet_from_events_raises_labor_cost(self):
		emp = employee("عامل التايمشيت")
		project = self.w.p1
		day = "2026-12-01"
		for event, at in (("In", f"{day} 08:00:00"), ("Out", f"{day} 14:00:00"), ("In", f"{day} 15:00:00")):
			frappe.get_doc(
				{
					"doctype": "Clock Event",
					"project": project,
					"event": event,
					"at": at,
					"employee": emp,
					"worker": "عامل التايمشيت",
					"inside_geofence": 1,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Crew",
				"crew_name": "فريق التايمشيت",
				"members": [{"worker_name": "عامل", "employee": emp, "daily_rate": 400}],
			}
		).insert(ignore_permissions=True)
		before = flt(frappe.db.get_value("Project", project, "total_costing_amount"))
		created = sitelog.build_timesheets(day)
		self.assertEqual(len(created), 1)
		ts = frappe.get_doc("Timesheet", created[0])
		self.assertEqual(ts.docstatus, 0, "draft for the engineer to review")
		self.assertEqual(flt(ts.time_logs[0].hours), 6.0)
		self.assertEqual(flt(ts.time_logs[0].costing_rate), 50.0)  # 400 ÷ 8 h
		self.assertTrue(
			frappe.db.get_value(
				"Clock Event", {"employee": emp, "event": "In", "at": f"{day} 15:00:00"}, "unpaired"
			)
		)
		ts.submit()
		after = flt(frappe.db.get_value("Project", project, "total_costing_amount"))
		self.assertEqual(flt(after - before, 2), 300.0)  # 6 h × 50

	def test_daily_log_one_per_day_and_client_view(self):
		with self.set_user(self.w.users.eng1):
			first = sitelog.save_daily_log(
				self.w.p1,
				{
					"log_date": nowdate(),
					"work_done": "بطانة غرفة النوم",
					"manpower": [{"trade": "محارة", "headcount": 5, "hours": 8}],
				},
			)
			again = sitelog.save_daily_log(self.w.p1, {"log_date": nowdate(), "issues": "تأخير الرمل"})
			self.assertEqual(first, again)
			sitelog.save_daily_log(
				self.w.p1, {"log_date": "2026-01-02", "work_done": "سر", "internal_only": 1}
			)
			tomorrow = sitelog.get_daily_log(self.w.p1, frappe.utils.add_days(nowdate(), 1))
		self.assertFalse(tomorrow["exists"])
		self.assertEqual(tomorrow["manpower"][0]["headcount"], 5, "defaults from the previous day")
		with self.set_user(self.w.users.client1):
			rows = sitelog.client_daily_logs(self.w.p1)
			self.assertRaises(frappe.PermissionError, frappe.client.get, "Daily Log", first)
		text = frappe.as_json(rows, ensure_ascii=False)
		self.assertIn("بطانة", text)
		self.assertNotIn("سر", text)
		self.assertNotIn("manpower", text)
		self.assertNotIn("headcount", text)
