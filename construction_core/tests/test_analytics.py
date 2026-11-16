"""Phase 17: WIP math on a seeded project, ties to ERPNext's own reports, engineer scoping,
and the 3-second target with 200 projects."""

import time

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from construction_core import analytics, money
from construction_core.tests.factories import get_company, make_milestone, make_project, make_world, stages_of
from construction_core.tests.test_money import make_customer, make_item, make_supplier, pay


def purchase(project: str, stage: str, amount: float, group="خامات", item="رمل التقارير") -> str:
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": make_supplier("مورد التقارير"),
			"company": get_company(),
			"project": project,
			"project_stage": stage,
			"posting_date": nowdate(),
			"disable_rounded_total": 1,
			"items": [{"item_code": make_item(item, group), "qty": 1, "rate": amount, "project": project}],
		}
	).insert(ignore_permissions=True)
	pi.submit()
	return pi.name


class TestWip(IntegrationTestCase):
	def test_wip_math_pure(self):
		r = analytics.wip_math(contract=100000, complete_pct=40, billed=50000, cost=30000, budget=70000)
		self.assertEqual(r["earned"], 40000)
		self.assertEqual(r["over_under"], 10000)  # billed ahead of the work
		self.assertEqual(r["eac"], 75000)  # 30,000 ÷ 0.4
		self.assertEqual(r["margin"], 25000)
		self.assertEqual(r["margin_pct"], 25)
		self.assertEqual(
			analytics.wip_math(100000, 0, 0, 0, 70000)["eac"], 70000, "budget before any progress"
		)

	def test_seeded_project_and_ties_to_erpnext(self):
		w = make_world()
		project = make_project("مشروع تقارير WIP", [w.users.eng1])
		frappe.db.set_value(
			"Project", project, {"customer": make_customer("عميل التقارير"), "estimated_costing": 70000}
		)
		stage = stages_of(project)[0]
		ms = [make_milestone(project, stage, a, f"دفعة {i}") for i, a in enumerate((30000, 70000))]
		frappe.db.set_value("Payment Milestone", ms[0], "status", "Due")
		si = frappe.get_doc("Sales Invoice", money.make_invoice(ms[0]))
		si.submit()
		pay(si.name, 10000)
		purchase(project, stage, 12000)
		# 40% complete
		frappe.db.set_value("Project", project, "weighted_progress", 40)

		row = next(r for r in analytics.wip({"project": project}))
		self.assertEqual(
			(row["contract"], row["earned"], row["billed"], row["over_under"], row["cost"]),
			(100000, 40000, 30000, -10000, 12000),
		)
		self.assertEqual(row["eac"], 30000)
		self.assertEqual(row["margin"], 70000)

		# job costing actual = the General Ledger's expense for the project
		actual = sum(r["actual"] for r in analytics.job_costing({"project": project}))
		gl = flt(
			frappe.db.sql(
				"""select sum(g.debit - g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
				where g.project = %s and g.is_cancelled = 0 and a.root_type = 'Expense'""",
				project,
			)[0][0],
			2,
		)
		self.assertEqual(actual, gl)
		self.assertEqual(actual, 12000)

		# collections outstanding = ERPNext Accounts Receivable for the same customer
		ours = sum(r["outstanding"] for r in analytics.collections({"project": project}))
		self.assertEqual(ours, 20000)
		from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as ar

		_cols, data, *_ = ar(
			{
				"company": get_company(),
				"report_date": nowdate(),
				"party_type": "Customer",
				"party": [make_customer("عميل التقارير")],
				"ageing_based_on": "Due Date",
				"range": "30, 60, 90, 120",
			}
		)
		erp = flt(sum(flt(d.get("outstanding")) for d in data if d.get("voucher_no") == si.name), 2)
		self.assertEqual(ours, erp)

		# the upcoming milestone shows in the next-60-days column
		frappe.db.set_value("Payment Milestone", ms[1], "due_date", add_days(nowdate(), 20))
		c = next(r for r in analytics.collections({"project": project}))
		self.assertEqual((c["next_30"], c["next_60"]), (70000, 70000))

		# schedule: a stage past its planned end shows the project late
		frappe.db.set_value(
			"Project Stage", stage, {"planned_end": add_days(nowdate(), -5), "status": "In Progress"}
		)
		late = [r for r in analytics.schedule_status({"project": project})]
		self.assertEqual(late[0]["days_late"], 5)

		# number cards / dashboard run
		d = analytics.dashboard({"project": project})
		self.assertEqual(d["active_projects"], 1)
		self.assertEqual(d["receivables"], 20000)


class TestScopingAndSpeed(IntegrationTestCase):
	def test_engineer_sees_only_own_projects_in_every_report(self):
		w = make_world()
		reports = [
			analytics.wip,
			analytics.job_costing,
			analytics.labor,
			analytics.collections,
			analytics.selections_status,
			analytics.schedule_status,
			analytics.budget_variance,
		]
		frappe.db.set_value(
			"Project Stage",
			stages_of(w.p2)[0],
			{"planned_end": add_days(nowdate(), -3), "status": "In Progress"},
		)
		with self.set_user(w.users.eng1):
			allowed = set(analytics.allowed_projects())
			self.assertIn(w.p1, allowed)
			self.assertNotIn(w.p2, allowed)
			for fn in reports:
				for row in fn({}):
					self.assertIn(row["project"], allowed, fn.__name__)
			self.assertNotIn(w.p2, [r["project"] for r in analytics.schedule_status({})])
			dash = analytics.engineer_dashboard()
			self.assertTrue(all(r.project in allowed for r in dash["overdue_selections"]))
		with self.set_user(w.users.client1):
			self.assertRaises(frappe.PermissionError, analytics.engineer_dashboard)

	def test_two_hundred_projects_under_three_seconds(self):
		company = get_company()
		existing = frappe.db.count("Project", {"project_name": ["like", "مشروع أداء %"]})
		for i in range(existing, 200):
			p = frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"مشروع أداء {i:03d}",
					"company": company,
					"weighted_progress": i % 100,
				}
			).insert(ignore_permissions=True)
			for j in range(3):
				frappe.get_doc(
					{
						"doctype": "Project Stage",
						"project": p.name,
						"stage_name": f"مرحلة {j}",
						"weight": 33,
						"sort_order": j,
					}
				).insert(ignore_permissions=True)
				frappe.get_doc(
					{
						"doctype": "Payment Milestone",
						"project": p.name,
						"label": f"دفعة {j}",
						"amount": 1000 * (j + 1),
					}
				).insert(ignore_permissions=True)
		timings = {}
		for fn in (
			analytics.wip,
			analytics.job_costing,
			analytics.budget_variance,
			analytics.labor,
			analytics.collections,
			analytics.selections_status,
			analytics.schedule_status,
			analytics.pipeline,
			analytics.dashboard,
		):
			start = time.perf_counter()
			fn({})
			timings[fn.__name__] = round(time.perf_counter() - start, 3)
		print("report timings (s) with", frappe.db.count("Project"), "projects:", timings)
		self.assertTrue(all(t < 3 for t in timings.values()), timings)
