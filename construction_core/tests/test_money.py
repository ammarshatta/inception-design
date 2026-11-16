"""Phase 6: milestone → invoice → payment, expenses, VAT, and the report against the GL."""

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate

from construction_core import money
from construction_core.api import portal
from construction_core.construction_core.report.project_financial_summary.project_financial_summary import (
	get_summary,
)
from construction_core.tests.factories import make_milestone, make_project, make_world, stages_of


def make_customer(name="عميل الحسابات") -> str:
	if frappe.db.exists("Customer", name):
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_type": "Individual",
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def make_supplier(name="مورد الرمل") -> str:
	if frappe.db.exists("Supplier", name):
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": name,
				"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def make_item(code, group) -> str:
	money.ensure_item_groups()
	if not frappe.db.exists("Item", code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": code,
				"item_group": group,
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_purchase_item": 1,
			}
		).insert(ignore_permissions=True)
	return code


def pay(si_name: str, amount=None):
	pe = get_payment_entry("Sales Invoice", si_name)
	if amount is not None:
		pe.paid_amount = amount
		pe.received_amount = amount
		pe.references[0].allocated_amount = amount
	pe.reference_no = "TEST-" + si_name
	pe.reference_date = nowdate()
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe


class TestMoney(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		money.ensure_finance_setup()

	def project_with_customer(self, title):
		project = make_project(title, [self.w.users.client1])
		frappe.db.set_value("Project", project, "customer", make_customer())
		return project

	def due_milestone(self, project, amount=85000, idx=0):
		m = make_milestone(project, stages_of(project)[idx], amount, f"دفعة {idx + 1}")
		frappe.db.set_value("Payment Milestone", m, "status", "Due")
		return m

	def test_full_cycle_and_cancel(self):
		project = self.project_with_customer("مشروع دورة الفلوس")
		m = self.due_milestone(project)
		si_name = money.make_invoice(m)
		si = frappe.get_doc("Sales Invoice", si_name)
		self.assertEqual(si.docstatus, 0)
		self.assertEqual(si.project, project)
		self.assertEqual(flt(si.items[0].rate), 85000)
		self.assertIn("دفعة", si.items[0].description)
		self.assertEqual(money.make_invoice(m), si_name, "a second click returns the same draft")
		si.submit()
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Invoiced")
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "sales_invoice"), si_name)

		pe = pay(si_name)
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Paid")
		with self.set_user(self.w.users.client1):
			rows = {r.name: r for r in portal.payments(project)["milestones"]}
		self.assertEqual(rows[m].status, "Paid")

		pe.cancel()
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Invoiced")

	def test_partial_payment_stays_invoiced(self):
		project = self.project_with_customer("مشروع دفع جزئي")
		m = self.due_milestone(project, 10000)
		si = frappe.get_doc("Sales Invoice", money.make_invoice(m))
		si.submit()
		pay(si.name, 4000)
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Invoiced")

	def test_only_due_can_be_invoiced(self):
		project = self.project_with_customer("مشروع دفعة جاية")
		m = make_milestone(project, stages_of(project)[0], 5000)
		self.assertRaises(frappe.ValidationError, money.make_invoice, m)

	def test_client_cannot_invoice(self):
		project = self.project_with_customer("مشروع صلاحية الفاتورة")
		m = self.due_milestone(project)
		with self.set_user(self.w.users.client1):
			self.assertRaises(frappe.PermissionError, money.make_invoice, m)

	def test_submitted_invoice_cannot_be_edited(self):
		project = self.project_with_customer("مشروع فاتورة مقفولة")
		si = frappe.get_doc("Sales Invoice", money.make_invoice(self.due_milestone(project)))
		si.submit()
		si.reload()
		si.items[0].rate = 1
		self.assertRaises(frappe.ValidationError, si.save)

	def test_vat_template_rate_from_accountant(self):
		company = frappe.db.get_value("Project", self.w.p1, "company")
		template = money.ensure_vat_template(company)
		self.assertTrue(template)
		t = frappe.get_doc("Sales Taxes and Charges Template", template)
		self.assertEqual(flt(t.taxes[0].rate), 0, "the rate is never hardcoded")
		t.taxes[0].rate = 14
		t.save(ignore_permissions=True)
		project = self.project_with_customer("مشروع الضريبة")
		si = frappe.get_doc("Sales Invoice", money.make_invoice(self.due_milestone(project, 1000)))
		from erpnext.controllers.accounts_controller import get_taxes_and_charges

		si.taxes_and_charges = template
		si.set("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", template))
		si.save()
		self.assertEqual(flt(si.total_taxes_and_charges, 2), 140.0)
		self.assertEqual(flt(si.grand_total, 2), 1140.0)
		t.reload()
		t.taxes[0].rate = 0
		t.save(ignore_permissions=True)

	def test_report_matches_general_ledger(self):
		project = self.project_with_customer("مشروع التقرير المالي")
		stages = stages_of(project)
		frappe.db.set_value("Project", project, "estimated_costing", 120000)
		inv = []
		for i, amount in enumerate((85000.55, 40000.25)):
			si = frappe.get_doc("Sales Invoice", money.make_invoice(self.due_milestone(project, amount, i)))
			si.submit()
			inv.append(si.name)
		make_milestone(project, stages[2], 30000, "دفعة جاية")
		pay(inv[0])
		pay(inv[1], 10000.10)

		company = frappe.db.get_value("Project", project, "company")
		supplier = make_supplier()
		for item, _group, stage, rate in (
			(make_item("رمل", "خامات"), "خامات", stages[0], 1500.5),
			(make_item("يومية محارة", "عمالة"), "عمالة", stages[1], 3200.25),
		):
			pi = frappe.get_doc(
				{
					"doctype": "Purchase Invoice",
					"company": company,
					"supplier": supplier,
					"project": project,
					"project_stage": stage,
					"items": [{"item_code": item, "qty": 2, "rate": rate, "project": project}],
				}
			)
			pi.insert(ignore_permissions=True)
			pi.submit()

		s = get_summary(project)
		self.assertEqual(s.contract_value, flt(85000.55 + 40000.25 + 30000, 2))

		gl_invoiced = flt(
			frappe.db.sql(
				"""select sum(debit - credit) from `tabGL Entry`
				where is_cancelled=0 and voucher_type='Sales Invoice' and voucher_no in %(inv)s
				and party_type='Customer'""",
				{"inv": inv},
			)[0][0],
			2,
		)
		gl_outstanding = flt(
			frappe.db.sql(
				"""select sum(debit - credit) from `tabGL Entry`
				where is_cancelled=0 and party_type='Customer' and against_voucher_type='Sales Invoice'
				and against_voucher in %(inv)s""",
				{"inv": inv},
			)[0][0],
			2,
		)
		gl_expenses = flt(
			frappe.db.sql(
				"""select sum(gle.debit - gle.credit) from `tabGL Entry` gle
				join `tabAccount` acc on acc.name = gle.account
				join `tabPurchase Invoice` pi on pi.name = gle.voucher_no
				where gle.is_cancelled=0 and gle.voucher_type='Purchase Invoice'
				and acc.root_type='Expense' and pi.project=%s""",
				project,
			)[0][0],
			2,
		)
		self.assertEqual(s.invoiced, gl_invoiced)
		self.assertEqual(s.outstanding, gl_outstanding)
		self.assertEqual(s.collected, flt(gl_invoiced - gl_outstanding, 2))
		self.assertEqual(s.expenses, gl_expenses)
		rounding = flt(
			frappe.db.sql(
				"select sum(base_rounding_adjustment) from `tabPurchase Invoice` where project=%s and docstatus=1",
				project,
			)[0][0],
			2,
		)
		self.assertEqual(s.expenses, flt(2 * 1500.5 + 2 * 3200.25 + rounding, 2))
		self.assertEqual(s.expenses_by_group["خامات"], 3001.0)
		self.assertEqual(s.budget, 120000)
		ar = flt(
			frappe.db.sql(
				"select sum(outstanding_amount) from `tabSales Invoice` where name in %(inv)s", {"inv": inv}
			)[0][0],
			2,
		)
		self.assertEqual(s.outstanding, ar)
