"""Phase 11: working days, slides with dependencies, roll-up, conflicts, foreman view."""

from datetime import date

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from construction_core import scheduling
from construction_core.tests.factories import make_project, stages_of


def task(project, subject, start, end, depends_on=None, stage=None):
	doc = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": subject,
			"project": project,
			"exp_start_date": start,
			"exp_end_date": end,
			"project_stage": stage,
			"depends_on": [{"task": depends_on}] if depends_on else [],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


class TestWorkingDays(IntegrationTestCase):
	def test_across_friday(self):
		# Thu 3 Dec 2026 + 1 working day = Sat 5 Dec (Friday skipped)
		off = set()
		self.assertEqual(scheduling.add_working_days(date(2026, 12, 3), 1, off), date(2026, 12, 5))
		self.assertEqual(scheduling.add_working_days(date(2026, 12, 3), 2, off), date(2026, 12, 6))

	def test_across_holiday(self):
		off = {date(2027, 1, 7), date(2027, 1, 8)}  # holiday (Thu) and Friday
		self.assertEqual(scheduling.add_working_days(date(2027, 1, 6), 1, off), date(2027, 1, 9))

	def test_holiday_list_has_fridays_and_fixed_days(self):
		scheduling.ensure_holiday_list(2026)
		off = scheduling.holidays()
		self.assertIn(date(2026, 12, 4), off)  # a Friday
		self.assertIn(date(2026, 10, 6), off)

	def test_chain_of_three(self):
		project = make_project("مشروع سلسلة المهام", [])
		off = {date(2026, 12, 4), date(2026, 12, 11)}  # Fridays
		a = task(project, "أ", "2026-12-01", "2026-12-02")
		b = task(project, "ب", "2026-12-03", "2026-12-05", depends_on=a)
		c = task(project, "ج", "2026-12-06", "2026-12-08", depends_on=b)
		self.assertEqual(scheduling.dependents(a), [b, c])
		from unittest.mock import patch

		with patch.object(scheduling, "holidays", return_value=off):
			preview = scheduling.slide_task(a, 2)
			self.assertEqual(
				getdate(frappe.db.get_value("Task", a, "exp_start_date")), date(2026, 12, 1), "preview only"
			)
			scheduling.slide_task(a, 2, apply=1)
		self.assertEqual([r["task"] for r in preview], [a, b, c])
		self.assertEqual(getdate(frappe.db.get_value("Task", a, "exp_start_date")), date(2026, 12, 3))
		self.assertEqual(getdate(frappe.db.get_value("Task", b, "exp_start_date")), date(2026, 12, 6))
		self.assertEqual(getdate(frappe.db.get_value("Task", c, "exp_end_date")), date(2026, 12, 10))


class TestRollUpAndConflicts(IntegrationTestCase):
	def test_stage_dates_follow_tasks(self):
		project = make_project("مشروع التجميع", [])
		stage = stages_of(project)[0]
		t1 = task(project, "تكسير 1", "2026-12-01", "2026-12-03", stage=stage)
		task(project, "تكسير 2", "2026-12-02", "2026-12-07", stage=stage)
		s = frappe.db.get_value("Project Stage", stage, ["planned_start", "planned_end"], as_dict=True)
		self.assertEqual(
			(getdate(s.planned_start), getdate(s.planned_end)), (date(2026, 12, 1), date(2026, 12, 7))
		)
		doc = frappe.get_doc("Task", t1)
		doc.exp_start_date = "2026-11-28"
		doc.save(ignore_permissions=True)
		self.assertEqual(
			getdate(frappe.db.get_value("Project Stage", stage, "planned_start")), date(2026, 11, 28)
		)

	def crew(self, name="فريق محارة اختبار", foreman=None):
		if not frappe.db.exists("Crew", name):
			frappe.get_doc(
				{
					"doctype": "Crew",
					"crew_name": name,
					"foreman_user": foreman,
					"members": [{"worker_name": "عم سعيد", "daily_rate": 650}],
				}
			).insert(ignore_permissions=True)
		return name

	def test_overlap_warns_and_names_project(self):
		p1 = make_project("مشروع الفريق الأول", [])
		p2 = make_project("مشروع الفريق التاني", [])
		crew = self.crew()
		frappe.get_doc(
			{
				"doctype": "Crew Assignment",
				"crew": crew,
				"project": p1,
				"from_date": "2026-12-01",
				"to_date": "2026-12-10",
			}
		).insert(ignore_permissions=True)
		frappe.clear_messages()
		second = frappe.get_doc(
			{
				"doctype": "Crew Assignment",
				"crew": crew,
				"project": p2,
				"from_date": "2026-12-08",
				"to_date": "2026-12-12",
			}
		).insert(ignore_permissions=True)
		self.assertIn("مشروع الفريق الأول", second.conflict_note)
		self.assertTrue(any("مشروع الفريق الأول" in str(m) for m in frappe.get_message_log()))
		comments = frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Crew Assignment", "reference_name": second.name},
			pluck="content",
		)
		self.assertTrue(any("التعارض" in (c or "") for c in comments))

	def test_foreman_sees_only_own_crew(self):
		from construction_core.tests.factories import make_user

		foreman = make_user("eng2")
		frappe.get_doc("User", foreman).add_roles("Construction Foreman")
		mine = self.crew("فريق الفورمان", foreman)
		other = self.crew("فريق تاني")
		p = make_project("مشروع الفورمان", [])
		today = nowdate()
		a = frappe.get_doc(
			{"doctype": "Crew Assignment", "crew": mine, "project": p, "from_date": today, "to_date": today}
		).insert(ignore_permissions=True)
		b = frappe.get_doc(
			{"doctype": "Crew Assignment", "crew": other, "project": p, "from_date": today, "to_date": today}
		).insert(ignore_permissions=True)
		with self.set_user(foreman):
			names = [r.name for r in scheduling.foreman_assignments("today")]
		self.assertIn(a.name, names)
		self.assertNotIn(b.name, names)
