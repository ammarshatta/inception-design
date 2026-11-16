"""Phases 9 and 10: selections, change orders, credits, schedule shift."""

from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from construction_core import change_orders, esign, selections
from construction_core.construction_core.report.purchase_list.purchase_list import get_rows
from construction_core.scheduling import shift_stages
from construction_core.tests.factories import make_project, make_world, stages_of
from construction_core.tests.test_esign import SIG, blank_pdf
from construction_core.tests.test_money import make_customer


def category(name="سيراميك أرضيات") -> str:
	if not frappe.db.exists("Selection Category", name):
		frappe.get_doc({"doctype": "Selection Category", "category_name": name}).insert(
			ignore_permissions=True
		)
	return name


def option(name, price, cat=None) -> str:
	existing = frappe.db.get_value("Selection Option", {"option_name": name}, "name")
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Selection Option",
				"category": cat or category(),
				"option_name": name,
				"unit_price": price,
				"brand": "كليوباترا",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestPriceDifference(IntegrationTestCase):
	def test_above_equal_below(self):
		# allowance 500/m² for 40 m² = 20,000
		self.assertEqual(selections.price_difference(650, 40, 20000), Decimal("6000.00"))
		self.assertEqual(selections.price_difference(500, 40, 20000), Decimal("0.00"))
		self.assertEqual(selections.price_difference(450, 40, 20000), Decimal("-2000.00"))
		self.assertEqual(selections.price_difference(450, 0, 20000), Decimal("0"))


class TestSelections(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		cls.cheap = option("سيراميك 450", 450)
		cls.exact = option("سيراميك 500", 500)
		cls.dear = option("بورسلين 650", 650)

	def new_selection(self, project=None, **kw):
		project = project or self.w.p1
		return frappe.get_doc(
			{
				"doctype": "Project Selection",
				"project": project,
				"category": category(),
				"room_or_area": "الريسبشن",
				"qty": 40,
				"allowance_amount": 20000,
				"due_date": add_days(nowdate(), 10),
				**kw,
			}
		).insert(ignore_permissions=True)

	def test_client_sees_live_difference(self):
		s = self.new_selection()
		with self.set_user(self.w.users.client1):
			rows = selections.project_selections(self.w.p1)
		row = next(r for r in rows if r.name == s.name)
		diffs = {o.option_name: o.difference for o in row.options}
		self.assertEqual(diffs["بورسلين 650"], Decimal("6000.00"))
		self.assertEqual(diffs["سيراميك 500"], Decimal("0.00"))

	def test_within_allowance_locks_without_signature(self):
		s = self.new_selection()
		with self.set_user(self.w.users.client1):
			selections.choose(s.name, self.cheap)
			res = selections.approve(s.name)
		self.assertEqual(res["status"], "Locked")
		self.assertFalse(frappe.db.get_value("Project Selection", s.name, "change_order"))

	def test_over_allowance_sign_creates_draft_change_order(self):
		s = self.new_selection()
		with self.set_user(self.w.users.client1), patch("frappe.get_print", side_effect=blank_pdf):
			selections.choose(s.name, self.dear)
			res = selections.approve(s.name)
		self.assertEqual(res["status"], "Awaiting Signature")
		captured = {}
		with patch.object(
			esign, "_deliver_otp", side_effect=lambda req, code: captured.setdefault("code", code)
		):
			with self.set_user(self.w.users.client1):
				esign.request_otp(res["signature_request"])
		with self.set_user(self.w.users.client1), patch("frappe.get_print", side_effect=blank_pdf):
			esign.sign(res["signature_request"], captured["code"], SIG)
		s.reload()
		self.assertEqual(s.status, "Locked")
		co = frappe.get_doc("Change Order", s.change_order)
		self.assertEqual(co.status, "Draft")
		self.assertEqual(co.source, "Selection")
		self.assertEqual(Decimal(str(co.cost_difference)), Decimal("6000.00"))

	def test_locked_cannot_change(self):
		s = self.new_selection()
		with self.set_user(self.w.users.client1):
			selections.choose(s.name, self.cheap)
			selections.approve(s.name)
			self.assertRaises(frappe.PermissionError, selections.choose, s.name, self.exact)
		with self.set_user(self.w.users.eng1):
			doc = frappe.get_doc("Project Selection", s.name)
			doc.qty = 50
			self.assertRaises(frappe.PermissionError, doc.save)
			self.assertRaises(frappe.PermissionError, selections.choose, s.name, self.exact)

	def test_purchase_list_only_approved(self):
		project = make_project("مشروع قائمة الشراء", [self.w.users.client1])
		approved = self.new_selection(project=project, qty=12)
		self.new_selection(project=project, qty=99)  # still open
		with self.set_user(self.w.users.client1):
			selections.choose(approved.name, self.cheap)
			selections.approve(approved.name)
		rows = get_rows(project)
		self.assertEqual([(r["selection"], r["qty"]) for r in rows], [(approved.name, 12)])

	def test_unlock_with_reason(self):
		s = self.new_selection()
		with self.set_user(self.w.users.client1):
			selections.choose(s.name, self.cheap)
			selections.approve(s.name)
		self.assertRaises(frappe.ValidationError, selections.unlock, s.name, "")
		name = selections.unlock(s.name, "الكمية غلط")
		self.assertEqual(name, s.name)
		self.assertEqual(frappe.db.get_value("Project Selection", s.name, "status"), "Open")
		with self.set_user(self.w.users.eng1):
			self.assertRaises(frappe.PermissionError, selections.unlock, s.name, "x")


class TestChangeOrders(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		frappe.db.set_value("Project", cls.w.p1, "customer", make_customer())

	def priced(self, amount, **kw):
		with self.set_user(self.w.users.client1):
			name = change_orders.request_change(self.w.p1, "عايز أغيّر مكان الحوض")
		co = frappe.get_doc("Change Order", name)
		co.append(
			"lines",
			{"section": "مطبخ", "line_type": "Other", "description": "تعديل", "qty": 1, "unit_cost": amount},
		)
		co.overhead_pct = 0
		co.profit_pct = 0
		for k, v in kw.items():
			co.set(k, v)
		co.save(ignore_permissions=True)
		return co

	def sign(self, co_name):
		change_orders.engineer_approve(co_name)
		with patch("frappe.get_print", side_effect=blank_pdf):
			req = change_orders.send_to_client(co_name)["request"]
		captured = {}
		with patch.object(
			esign, "_deliver_otp", side_effect=lambda r, code: captured.setdefault("code", code)
		):
			with self.set_user(self.w.users.client1):
				esign.request_otp(req)
		with self.set_user(self.w.users.client1), patch("frappe.get_print", side_effect=blank_pdf):
			esign.sign(req, captured["code"], SIG)

	def test_positive_cycle_creates_milestone_and_budget(self):
		budget_before = Decimal(str(frappe.db.get_value("Project", self.w.p1, "estimated_costing") or 0))
		co = self.priced(5000)
		self.assertEqual(co.source, "Client Request")
		self.sign(co.name)
		co.reload()
		self.assertEqual(co.status, "Approved")
		self.assertEqual(co.docstatus, 1)
		m = frappe.get_doc("Payment Milestone", co.payment_milestone)
		self.assertEqual(Decimal(str(m.amount)), Decimal("5000"))
		budget_after = Decimal(str(frappe.db.get_value("Project", self.w.p1, "estimated_costing")))
		self.assertEqual(budget_after - budget_before, Decimal("5000"))

	def test_approved_cannot_be_edited(self):
		co = self.priced(1000)
		self.sign(co.name)
		co.reload()
		co.lines[0].qty = 3
		self.assertRaises(frappe.ValidationError, co.save)

	def test_client_cannot_skip_chain(self):
		co = self.priced(1000)
		self.assertRaises(frappe.ValidationError, change_orders.send_to_client, co.name)
		with self.set_user(self.w.users.client1):
			self.assertRaises(frappe.PermissionError, change_orders.engineer_approve, co.name)
		doc = frappe.get_doc("Change Order", co.name)
		doc.status = "Approved"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_negative_credit_note_in_receivables(self):
		from construction_core import money

		m = frappe.get_doc(
			{
				"doctype": "Payment Milestone",
				"project": self.w.p1,
				"label": "دفعة للفاتورة",
				"amount": 10000,
				"status": "Due",
			}
		).insert(ignore_permissions=True)
		si = frappe.get_doc("Sales Invoice", money.make_invoice(m.name))
		si.submit()
		co = self.priced(-2000, credit_mode="Credit note")
		self.sign(co.name)
		co.reload()
		self.assertTrue(co.credit_note)
		credit = frappe.get_doc("Sales Invoice", co.credit_note)
		credit.submit()
		customer = frappe.db.get_value("Project", self.w.p1, "customer")
		ar = frappe.db.sql(
			"""select sum(debit - credit) from `tabGL Entry` where is_cancelled=0 and party_type='Customer'
			and party=%s and voucher_no in (%s, %s)""",
			(customer, si.name, credit.name),
		)[0][0]
		self.assertEqual(Decimal(str(ar)), Decimal("8000.00"))

	def test_negative_reduces_next_milestone(self):
		project = make_project("مشروع خصم الدفعة", [self.w.users.client1])
		m = frappe.get_doc(
			{"doctype": "Payment Milestone", "project": project, "label": "دفعة جاية", "amount": 9000}
		).insert(ignore_permissions=True)
		with self.set_user(self.w.users.eng1):
			pass
		co = frappe.get_doc(
			{
				"doctype": "Change Order",
				"project": project,
				"title": "إلغاء بند",
				"overhead_pct": 0,
				"profit_pct": 0,
				"lines": [
					{
						"section": "حمام",
						"line_type": "Other",
						"description": "إلغاء",
						"qty": -1,
						"unit_cost": 1500,
					}
				],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(Decimal(str(co.cost_difference)), Decimal("-1500.00"))
		co.status = "Approved"
		co.flags.allow_status = True
		co.submit()
		change_orders.apply_effects(co)
		self.assertEqual(
			Decimal(str(frappe.db.get_value("Payment Milestone", m.name, "amount"))), Decimal("7500")
		)


class TestScheduleShift(IntegrationTestCase):
	def test_shift_moves_stage_and_following(self):
		project = make_project("مشروع الجدول", [])
		names = stages_of(project)
		for i, n in enumerate(names):
			frappe.db.set_value(
				"Project Stage",
				n,
				{
					"planned_start": add_days("2026-12-01", i * 10),
					"planned_end": add_days("2026-12-09", i * 10),
				},
			)
		frappe.db.set_value("Project Stage", names[3], "status", "Done")
		moved = shift_stages(project, names[2], 5)
		self.assertNotIn(names[0], moved)
		self.assertIn(names[2], moved)
		self.assertNotIn(names[3], moved, "a Done stage is not moved")
		self.assertEqual(
			getdate(frappe.db.get_value("Project Stage", names[2], "planned_start")), getdate("2026-12-26")
		)
		self.assertEqual(
			getdate(frappe.db.get_value("Project Stage", names[1], "planned_start")), getdate("2026-12-11")
		)
		self.assertEqual(
			getdate(frappe.db.get_value("Project Stage", names[4], "planned_end")), getdate("2027-01-14")
		)
