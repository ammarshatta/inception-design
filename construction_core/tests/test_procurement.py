"""Phase 13: needs → material requests, RFQ comparison → PO, committed cost, on-site receipt,
subcontracts signed by the subcontractor, progress claims (مستخلصات), retention."""

import base64
import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate
from PIL import Image

from construction_core import esign, procurement, subcontracts
from construction_core.tests.factories import get_company, make_world, stages_of
from construction_core.tests.test_esign import SIG, blank_pdf
from construction_core.tests.test_estimating import item, price
from construction_core.tests.test_money import make_customer


def supplier(name: str, group: str = "موردين خامات") -> str:
	subcontracts.ensure_supplier_groups()
	if not frappe.db.exists("Supplier", name):
		frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "supplier_group": group}).insert(
			ignore_permissions=True
		)
	return name


def photo_data_url() -> str:
	img = Image.new("RGB", (2400, 1800), (180, 170, 150))
	out = io.BytesIO()
	img.save(out, format="JPEG", quality=95)
	return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


def stage_named(project: str, stage_name: str) -> str:
	return frappe.db.get_value("Project Stage", {"project": project, "stage_name": stage_name}, "name")


def gl_balance(account: str) -> float:
	return flt(
		frappe.db.sql(
			"select ifnull(sum(credit - debit), 0) from `tabGL Entry` where account=%s and is_cancelled=0",
			account,
		)[0][0],
		2,
	)


class TestNeedsAndOrders(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		subcontracts.ensure_procurement_setup()
		cls.project = cls.w.p1
		day = add_days(nowdate(), -30)
		price("أسمنت المشتريات", 100, day)
		price("رمل المشتريات", 50, day)
		if not frappe.db.exists("Assembly", "محارة المشتريات"):
			frappe.get_doc(
				{
					"doctype": "Assembly",
					"assembly_name": "محارة المشتريات",
					"uom": "Nos",
					"items": [
						{
							"line_type": "Material",
							"item": item("رمل المشتريات"),
							"qty_per_unit": 2,
							"waste_pct": 0,
						}
					],
				}
			).insert(ignore_permissions=True)
		est = frappe.get_doc(
			{
				"doctype": "Estimate",
				"title": "مقايسة المشتريات",
				"customer": make_customer("عميل المشتريات"),
				"project": cls.project,
				"estimate_date": nowdate(),
				"lines": [
					{
						"section": "محارة",
						"line_type": "Material",
						"item": item("أسمنت المشتريات"),
						"qty": 10,
						"waste_pct": 10,
					},
					{"section": "محارة", "line_type": "Assembly", "assembly": "محارة المشتريات", "qty": 5},
					{
						"section": "دهانات",
						"line_type": "Other",
						"description": "مصنعية",
						"qty": 1,
						"unit_cost": 100,
					},
				],
			}
		).insert(ignore_permissions=True)
		est.submit()
		cat = (
			frappe.db.exists("Selection Category", "سيراميك المشتريات")
			or frappe.get_doc({"doctype": "Selection Category", "category_name": "سيراميك المشتريات"})
			.insert(ignore_permissions=True)
			.name
		)
		opt = frappe.get_doc(
			{
				"doctype": "Selection Option",
				"category": cat,
				"option_name": "سيراميك 60×60",
				"item": item("سيراميك المشتريات"),
				"unit_price": 300,
				"active": 1,
			}
		).insert(ignore_permissions=True)
		sel = frappe.get_doc(
			{
				"doctype": "Project Selection",
				"project": cls.project,
				"project_stage": stage_named(cls.project, "أرضيات وسيراميك"),
				"category": cat,
				"title": "سيراميك الريسبشن",
				"qty": 40,
				"uom": "Nos",
				"allowance_amount": 12000,
			}
		).insert(ignore_permissions=True)
		sel.db_set({"status": "Approved", "chosen_option": opt.name})

	def test_1_material_requests_per_stage_once(self):
		created = procurement.make_material_requests(self.project)
		self.assertEqual(len(created), 2)  # محارة, أرضيات وسيراميك (Other lines are not materials)
		items = {}
		for mr in created:
			doc = frappe.get_doc("Material Request", mr)
			self.assertEqual(doc.docstatus, 0)
			for it in doc.items:
				self.assertEqual(it.project, self.project)
				self.assertGreaterEqual(str(it.schedule_date), nowdate())
				items[it.item_code] = (flt(it.qty), it.project_stage)
		self.assertEqual(items["أسمنت المشتريات"], (11.0, stage_named(self.project, "محارة")))
		self.assertEqual(items["رمل المشتريات"], (10.0, stage_named(self.project, "محارة")))
		self.assertEqual(items["سيراميك المشتريات"], (40.0, stage_named(self.project, "أرضيات وسيراميك")))
		self.assertEqual(procurement.make_material_requests(self.project), [], "needs are requested once")

	def test_2_rfq_comparison_po_receipt_invoice(self):
		company = get_company()
		stage = stage_named(self.project, "محارة")
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": company,
				"schedule_date": add_days(nowdate(), 5),
				"items": [
					{
						"item_code": item("أسمنت المشتريات"),
						"qty": 20,
						"schedule_date": add_days(nowdate(), 5),
						"project": self.project,
						"project_stage": stage,
					}
				],
			}
		).insert(ignore_permissions=True)
		mr.submit()
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
			make_supplier_quotation_from_rfq,
		)
		from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order
		from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

		rfq = make_request_for_quotation(mr.name)
		names = [supplier(n) for n in ("مورد أ", "مورد ب", "مورد ج")]
		rfq.suppliers = []
		for s in names:
			rfq.append("suppliers", {"supplier": s, "send_email": 0})
		rfq.message_for_supplier = "برجاء التسعير"
		rfq.insert(ignore_permissions=True)
		rfq.submit()
		self.assertEqual(rfq.items[0].project_stage, stage)
		sqs = {}
		for s, rate in zip(names, (120, 95, 110), strict=True):
			sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=s)
			sq.items[0].rate = rate
			sq.insert(ignore_permissions=True)
			sq.submit()
			sqs[s] = sq.name
		from erpnext.buying.report.supplier_quotation_comparison.supplier_quotation_comparison import (
			execute as compare,
		)

		_, data, *_ = compare(
			{
				"company": company,
				"from_date": add_days(nowdate(), -1),
				"to_date": add_days(nowdate(), 1),
				"request_for_quotation": rfq.name,
				"categorize_by": "Categorize by Item",
			}
		)
		rates = {r.get("supplier_name"): flt(r.get("price")) for r in data if r.get("supplier_name")}
		self.assertEqual(rates, {"مورد أ": 2400.0, "مورد ب": 1900.0, "مورد ج": 2200.0})  # 20 × rate

		po = make_purchase_order(sqs["مورد ب"])
		po.schedule_date = add_days(nowdate(), 5)
		po.insert(ignore_permissions=True)
		po.submit()
		self.assertEqual((po.items[0].project, po.items[0].project_stage), (self.project, stage))

		from construction_core.construction_core.report.committed_cost.committed_cost import get_data

		committed = [r for r in get_data(frappe._dict(project=self.project)) if r["document"] == po.name]
		self.assertEqual([(r["project_stage"], r["committed"]) for r in committed], [(stage, 1900.0)])

		# on site: the engineer confirms with a photo; another project's engineer cannot
		with self.set_user(self.w.users.eng2):
			self.assertRaises(frappe.PermissionError, procurement.confirm_delivery, po.name, photo_data_url())
		with self.set_user(self.w.users.eng1):
			self.assertIn(po.name, [o["name"] for o in procurement.open_deliveries(self.project)])
			pr_name = procurement.confirm_delivery(po.name, photo_data_url())
		pr = frappe.get_doc("Purchase Receipt", pr_name)
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.confirmed_on_site_by, self.w.users.eng1)
		f = frappe.get_doc("File", {"file_url": pr.delivery_note_photo})
		self.assertTrue(f.is_private)
		self.assertEqual((f.attached_to_doctype, f.attached_to_name), ("Purchase Receipt", pr.name))
		with Image.open(f.get_full_path()) as img:
			self.assertLessEqual(max(img.size), 1600)
		self.assertEqual(flt(frappe.db.get_value("Purchase Order", po.name, "per_received")), 100)

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		from construction_core.construction_core.report.project_financial_summary.project_financial_summary import (
			get_summary,
		)

		before = flt(get_summary(self.project).expenses_by_stage.get("محارة"))
		pi = make_purchase_invoice(pr.name)
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.items[0].project_stage, stage)
		after = flt(get_summary(self.project).expenses_by_stage.get("محارة"))
		self.assertEqual(flt(after - before, 2), 1900.0)
		committed = [r for r in get_data(frappe._dict(project=self.project)) if r["document"] == po.name]
		self.assertEqual(committed, [], "billed, so no longer committed")


class TestSubcontracts(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		subcontracts.ensure_procurement_setup()
		cls.project = cls.w.p1
		cls.supplier = supplier("مقاول المحارة", "مقاولين باطن")
		cls.signer = "cc-sub1@example.com"
		if not frappe.db.exists("User", cls.signer):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": cls.signer,
					"first_name": "مقاول",
					"last_name": "الباطن",
					"user_type": "Website User",
					"send_welcome_email": 0,
					"mobile_no": "01000000123",
				}
			).insert(ignore_permissions=True)
			u.add_roles("Construction Subcontractor")

	def new_subcontract(self, title, advance=20000):
		return frappe.get_doc(
			{
				"doctype": "Subcontract",
				"title": title,
				"supplier": self.supplier,
				"project": self.project,
				"signer_user": self.signer,
				"retention_pct": 10,
				"advance_amount": advance,
				"lines": [
					{
						"description": "بطانة",
						"qty": 500,
						"uom": "Nos",
						"rate": 120,
						"project_stage": stage_named(self.project, "محارة"),
					},
					{
						"description": "دهانات",
						"qty": 200,
						"uom": "Nos",
						"rate": 200,
						"project_stage": stage_named(self.project, "دهانات"),
					},
				],
			}
		).insert(ignore_permissions=True)

	def claim(self, sub, q1, q2, override=0):
		c = frappe.get_doc({"doctype": "Subcontract Claim", "subcontract": sub.name, "period_to": nowdate()})
		c.insert(ignore_permissions=True)
		qty = {"بطانة": q1, "دهانات": q2}
		for line in c.lines:
			line.current_qty = qty[line.description]
		if override:
			c.admin_override = 1
			c.override_reason = "أعمال إضافية بأمر تغيير"
		c.save(ignore_permissions=True)
		return c

	def test_signing_activates_and_freezes(self):
		sub = self.new_subcontract("عقد التوقيع", advance=0)
		self.assertEqual(sub.contract_value, 100000)
		self.assertRaises(frappe.ValidationError, sub.submit)  # not signed
		with patch("frappe.get_print", side_effect=blank_pdf):
			links = subcontracts.send_for_signature(sub.name)
		request = links["request"]
		self.assertEqual(frappe.db.get_value("Subcontract", sub.name, "status"), "Awaiting Signature")
		captured = {}
		with patch.object(
			esign, "_deliver_otp", side_effect=lambda req, code: captured.setdefault("code", code)
		):
			with self.set_user(self.signer):
				self.assertEqual([r.name for r in esign.my_signature_requests()], [request])
				esign.request_otp(request)
		with self.set_user(self.signer), patch("frappe.get_print", side_effect=blank_pdf):
			esign.get_request(request)
			self.assertEqual(esign.sign(request, captured["code"], SIG)["status"], "Signed")
		sub.reload()
		self.assertEqual((sub.docstatus, sub.status), (1, "Active"))
		sub.lines[0].rate = 999
		self.assertRaises(frappe.UpdateAfterSubmitError, sub.save)
		# the subcontractor sees nothing of the project
		with self.set_user(self.signer):
			self.assertFalse(frappe.has_permission("Project", "read", self.project))
			self.assertFalse(frappe.has_permission("Subcontract", "read", sub.name))

	def test_three_claims_retention_advance_and_release(self):
		sub = self.new_subcontract("عقد المستخلصات")
		subcontracts.activate(sub)
		company = sub.company
		retention_acc = subcontracts.ensure_account(company, "retention")
		advance_acc = subcontracts.ensure_account(company, "advance")
		ret0, adv0 = gl_balance(retention_acc), gl_balance(advance_acc)
		advance_je = subcontracts.pay_advance(sub.name)
		self.assertEqual(flt(adv0 - gl_balance(advance_acc), 2), 20000.0, "advance paid out")
		self.assertTrue(frappe.db.get_value("Journal Entry", advance_je, "docstatus") == 1)

		# hand calculation: contract 100,000; retention 10%; advance 20,000 recovered pro rata
		expected = [
			# (q1, q2, previous بطانة, gross, retention, advance, net)
			(100, 50, 0, 22000, 2200, 4400, 15400),
			(200, 50, 100, 34000, 3400, 6800, 23800),
			(200, 100, 300, 44000, 4400, 8800, 30800),
		]
		for no, (q1, q2, prev, gross, ret, adv, net) in enumerate(expected, start=1):
			with self.set_user(self.w.users.eng1):
				c = self.claim(sub, q1, q2)
			self.assertEqual(c.claim_no, no)
			self.assertEqual(flt(c.lines[0].previous_qty), prev, "previous quantity pulled in")
			self.assertEqual(
				(flt(c.gross), flt(c.retention_amount), flt(c.advance_recovery), flt(c.net_due)),
				(gross, ret, adv, net),
			)
			with self.set_user(self.w.users.eng1):
				self.assertRaises(frappe.PermissionError, c.submit)  # the admin approves
			c.reload()
			c.submit()
			pi = frappe.get_doc("Purchase Invoice", c.purchase_invoice)
			self.assertEqual((pi.docstatus, flt(pi.grand_total), flt(pi.net_total)), (1, net, gross))
			self.assertEqual(pi.supplier, self.supplier)

		self.assertEqual(flt(gl_balance(retention_acc) - ret0, 2), 10000.0)
		self.assertEqual(flt(adv0 - gl_balance(advance_acc), 2), 0.0, "advance fully recovered")
		totals = subcontracts.subcontract_totals(sub.name)
		self.assertEqual((totals.claimed, totals.retention, totals.advance_recovered), (100000, 10000, 20000))

		res = subcontracts.release_retention(sub.name)
		self.assertEqual(res["amount"], 10000)
		self.assertEqual(frappe.db.get_value("Payment Entry", res["payment_entry"], "docstatus"), 1)
		self.assertEqual(flt(gl_balance(retention_acc) - ret0, 2), 0.0)
		self.assertEqual(frappe.db.get_value("Subcontract", sub.name, "status"), "Completed")
		self.assertRaises(frappe.ValidationError, subcontracts.release_retention, sub.name)

		from construction_core.construction_core.report.committed_cost.committed_cost import get_data

		self.assertFalse(
			[r for r in get_data(frappe._dict(project=self.project)) if r["document"] == sub.name]
		)

	def test_over_quantity_needs_admin_override(self):
		sub = self.new_subcontract("عقد التجاوز", advance=0)
		subcontracts.activate(sub)
		c = self.claim(sub, 510, 0)
		self.assertEqual(flt(c.lines[0].cumulative_qty), 510)
		self.assertRaises(frappe.ValidationError, c.submit)
		with self.set_user(self.w.users.eng1):
			c2 = frappe.get_doc("Subcontract Claim", c.name)
			c2.admin_override = 1
			c2.override_reason = "x"
			self.assertRaises(frappe.PermissionError, c2.save)
		c.reload()
		c.admin_override = 1
		c.override_reason = "أعمال إضافية بأمر تغيير"
		c.save()
		c.submit()
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "Subcontract Claim", "reference_name": c.name, "comment_type": "Info"},
			)
		)
		# committed cost: the rest of the contract (دهانات 40,000) is still committed under its stage
		from construction_core.construction_core.report.committed_cost.committed_cost import get_data

		rows = [r for r in get_data(frappe._dict(project=self.project)) if r["document"] == sub.name]
		self.assertEqual(
			[(r["project_stage"], r["committed"]) for r in rows],
			[(stage_named(self.project, "دهانات"), 40000.0)],
		)

	def test_stages_must_belong_to_the_project(self):
		bad = frappe.get_doc(
			{
				"doctype": "Subcontract",
				"title": "عقد غلط",
				"supplier": self.supplier,
				"project": self.project,
				"lines": [
					{"description": "x", "qty": 1, "rate": 1, "project_stage": stages_of(self.w.p2)[0]}
				],
			}
		)
		self.assertRaises(frappe.ValidationError, bad.insert, ignore_permissions=True)
