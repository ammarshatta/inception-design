"""Phase 7: costing engine, price library, estimates, revisions, quotation, pipeline."""

from decimal import Decimal

import frappe
from frappe.tests import IntegrationTestCase

from construction_core import money, sales
from construction_core.costing import engine
from construction_core.costing.engine import D


def item(code: str) -> str:
	money.ensure_item_groups()
	if not frappe.db.exists("Item", code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": code,
				"item_group": "خامات",
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)
	return code


def price(code: str, rate, valid_from: str):
	engine.ensure_price_list()
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item(code),
			"price_list": engine.BUYING_PRICE_LIST,
			"price_list_rate": rate,
			"valid_from": valid_from,
			"price_source": "Quotation",
		}
	).insert(ignore_permissions=True)


def labor(labor_type: str, rate, valid_from: str, governorate: str = ""):
	frappe.get_doc(
		{
			"doctype": "Labor Rate",
			"labor_type": labor_type,
			"uom": "Nos",
			"rate": rate,
			"valid_from": valid_from,
			"governorate": governorate,
		}
	).insert(ignore_permissions=True)


def customer() -> str:
	from construction_core.tests.test_money import make_customer

	return make_customer("عميل التسعير")


def vat_template(rate=14) -> str:
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	name = money.ensure_vat_template(company)
	t = frappe.get_doc("Sales Taxes and Charges Template", name)
	t.taxes[0].rate = rate
	t.save(ignore_permissions=True)
	return name


class TestEngine(IntegrationTestCase):
	def test_known_totals_pure(self):
		# Material: 10 × 100 × 1.05 = 1050.00; Labour: 10 × 50 = 500.00
		lines = [
			{"Material": D(10) * D(100) * D("1.05"), "Labor": D(0), "Equipment": D(0), "Other": D(0)},
			{"Material": D(0), "Labor": D(10) * D(50), "Equipment": D(0), "Other": D(0)},
		]
		res = engine.compute(lines, 10, 15, 14)
		self.assertEqual(res["line_totals"], [Decimal("1050.00"), Decimal("500.00")])
		self.assertEqual(res["subtotal"], Decimal("1550.00"))
		self.assertEqual(res["overhead"], Decimal("155.0000"))
		self.assertEqual(res["profit"], Decimal("255.750000"))
		# taxable 1960.75; VAT 274.505; total 2235.255 → 2235.26 (half up)
		self.assertEqual(res["grand_total"], Decimal("2235.26"))

	def test_rounding_only_on_lines_and_total(self):
		# three lines of 0.333… each: line totals round to 0.33, subtotal 0.99
		third = D(1) / D(3)
		lines = [{"Material": third, "Labor": D(0), "Equipment": D(0), "Other": D(0)}] * 3
		res = engine.compute(lines, 0, 0, 0)
		self.assertEqual(res["subtotal"], Decimal("0.99"))
		self.assertEqual(res["grand_total"], Decimal("0.99"))


class TestPriceLibrary(IntegrationTestCase):
	def test_price_in_force_on_date(self):
		price("رمل اختبار", 100, "2026-01-01")
		price("رمل اختبار", 130, "2026-03-01")
		self.assertEqual(engine.material_price("رمل اختبار", "2026-02-15"), D(100))
		self.assertEqual(engine.material_price("رمل اختبار", "2026-03-02"), D(130))

	def test_prices_cannot_be_deleted(self):
		price("أسمنت اختبار", 90, "2026-01-01")
		name = frappe.db.get_value("Item Price", {"item_code": "أسمنت اختبار"}, "name")
		self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Item Price", name)
		self.assertTrue(frappe.db.exists("Item Price", name))

	def test_labor_rate_governorate_first(self):
		labor("مصنعية اختبار", 100, "2026-01-01")
		labor("مصنعية اختبار", 120, "2026-01-01", "الجيزة")
		self.assertEqual(engine.labor_price("مصنعية اختبار", "2026-02-01", "الجيزة"), D(120))
		self.assertEqual(engine.labor_price("مصنعية اختبار", "2026-02-01", "القاهرة"), D(100))

	def test_import_prices_with_row_errors(self):
		item("بلاط استيراد")
		csv_text = (
			"type,item_or_labor,uom,rate,valid_from,governorate,source,source_ref\n"
			"material,بلاط استيراد,Nos,250,2026-02-01,,Quotation,عرض 1\n"
			"labor,مصنعية استيراد,Nos,80,2026-02-01,,Market survey,\n"
			"material,صنف مش موجود,Nos,10,2026-02-01,,Quotation,\n"
			"wood,x,Nos,1,2026-02-01,,,\n"
		)
		f = frappe.get_doc(
			{"doctype": "File", "file_name": "prices.csv", "content": csv_text.encode(), "is_private": 1}
		).insert(ignore_permissions=True)
		res = sales.import_prices(f.file_url)
		self.assertEqual(res["created"], 2)
		self.assertEqual([e["row"] for e in res["errors"]], [4, 5])


class TestEstimates(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		price("سيراميك 60", 300, "2026-01-01")
		price("لاصق سيراميك", 40, "2026-01-01")
		price("ترويبة", 20, "2026-01-01")
		labor("مصنعية سيراميك", 90, "2026-01-01")
		if not frappe.db.exists("Assembly", "متر سيراميك أرضيات شامل"):
			frappe.get_doc(
				{
					"doctype": "Assembly",
					"assembly_name": "متر سيراميك أرضيات شامل",
					"uom": "Nos",
					"items": [
						{"line_type": "Material", "item": "سيراميك 60", "qty_per_unit": 1, "waste_pct": 10},
						{
							"line_type": "Material",
							"item": "لاصق سيراميك",
							"qty_per_unit": 0.25,
							"waste_pct": 5,
						},
						{"line_type": "Material", "item": "ترويبة", "qty_per_unit": 0.1, "waste_pct": 0},
						{
							"line_type": "Labor",
							"labor_type": "مصنعية سيراميك",
							"qty_per_unit": 1,
							"waste_pct": 0,
						},
					],
				}
			).insert(ignore_permissions=True)

	def new_estimate(self, lines, **kw):
		doc = frappe.get_doc(
			{
				"doctype": "Estimate",
				"title": "تسعير اختبار",
				"customer": customer(),
				"estimate_date": "2026-02-01",
				"overhead_pct": 10,
				"profit_pct": 15,
				"lines": lines,
				**kw,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_assembly_for_50_m2(self):
		# per m²: 300×1.1 + 40×0.25×1.05 + 20×0.1 + 90 = 330 + 10.5 + 2 + 90 = 432.5
		parts = engine.assembly_unit_cost("متر سيراميك أرضيات شامل", "2026-02-01")
		self.assertEqual(parts["Material"], Decimal("342.5"))
		self.assertEqual(parts["Labor"], Decimal("90"))
		est = self.new_estimate(
			[
				{
					"section": "الريسبشن",
					"line_type": "Assembly",
					"assembly": "متر سيراميك أرضيات شامل",
					"qty": 50,
				}
			]
		)
		self.assertEqual(D(est.lines[0].line_total), Decimal("21625.00"))
		self.assertEqual(D(est.material_total), Decimal("17125.00"))
		self.assertEqual(D(est.labor_total), Decimal("4500.00"))

	def test_estimate_total_with_vat(self):
		est = self.new_estimate(
			[
				{"section": "أ", "line_type": "Material", "item": "سيراميك 60", "qty": 10, "waste_pct": 5},
				{"section": "ب", "line_type": "Labor", "labor_type": "مصنعية سيراميك", "qty": 10},
			],
			taxes_template=vat_template(14),
		)
		# 10×300×1.05 = 3150; 10×90 = 900; subtotal 4050; +10% = 4455; +15% = 5123.25; ×1.14 = 5840.505 → 5840.51
		self.assertEqual(D(est.grand_total), Decimal("5840.51"))

	def test_approved_estimate_keeps_captured_price(self):
		est = self.new_estimate([{"section": "أ", "line_type": "Material", "item": "ترويبة", "qty": 100}])
		self.assertEqual(D(est.lines[0].unit_cost), D(20))
		est.submit()
		price("ترويبة", 99, "2026-01-15")  # a new price, dated before the estimate date
		est.reload()
		self.assertEqual(D(est.lines[0].unit_cost), D(20))
		self.assertEqual(
			D(est.grand_total),
			engine.compute(
				[{"Material": D(2000), "Labor": D(0), "Equipment": D(0), "Other": D(0)}], 10, 15, 0
			)["grand_total"],
		)
		est.reload()
		est.overhead_pct = 50
		self.assertRaises(frappe.ValidationError, est.save)

	def test_revise_and_compare(self):
		est = self.new_estimate(
			[
				{"section": "مطبخ", "line_type": "Material", "item": "سيراميك 60", "qty": 10},
				{"section": "حمام", "line_type": "Material", "item": "لاصق سيراميك", "qty": 5},
				{"section": "ريسبشن", "line_type": "Labor", "labor_type": "مصنعية سيراميك", "qty": 4},
			]
		)
		est.submit()
		new_name = sales.revise(est.name)
		self.assertEqual(frappe.db.get_value("Estimate", est.name, "status"), "Superseded")
		new = frappe.get_doc("Estimate", new_name)
		self.assertEqual(new.revision, 2)
		self.assertEqual(new.previous_revision, est.name)
		new.lines = [ln for ln in new.lines if ln.section != "حمام"]  # removed
		new.lines[0].qty = 12  # changed: +2 × 300 = +600
		new.append(
			"lines", {"section": "بلكونة", "line_type": "Material", "item": "لاصق سيراميك", "qty": 2.5}
		)  # added: 2.5 × 40 = 100
		new.save(ignore_permissions=True)
		diff = sales.compare_revisions(est.name, new_name)
		self.assertEqual([r["section"] for r in diff["added"]], ["بلكونة"])
		self.assertEqual([r["section"] for r in diff["removed"]], ["حمام"])
		self.assertEqual(len(diff["changed"]), 1)
		self.assertEqual(diff["changed"][0]["difference"], Decimal("600.00"))
		self.assertEqual(diff["added_total"], Decimal("100.00"))
		self.assertEqual(diff["removed_total"], Decimal("200.00"))

	def test_quotation_one_line_per_section(self):
		est = self.new_estimate(
			[
				{"section": "مطبخ", "line_type": "Material", "item": "سيراميك 60", "qty": 3},
				{"section": "مطبخ", "line_type": "Labor", "labor_type": "مصنعية سيراميك", "qty": 3},
				{"section": "حمام", "line_type": "Material", "item": "ترويبة", "qty": 7},
			]
		)
		est.submit()
		q = frappe.get_doc("Quotation", sales.make_quotation(est.name))
		self.assertEqual(sorted(i.item_name for i in q.items), sorted(["مطبخ", "حمام"]))
		self.assertEqual(q.estimate, est.name)
		self.assertEqual(frappe.db.get_value("Estimate", est.name, "quotation"), q.name)
		taxable = D(est.subtotal) + D(est.overhead_amount) + D(est.profit_amount)
		self.assertLessEqual(abs(sum(D(i.amount) for i in q.items) - taxable), Decimal("0.01"))


class TestPipeline(IntegrationTestCase):
	def test_lead_to_opportunity_starts_new(self):
		from erpnext.crm.doctype.lead.lead import make_opportunity

		sales.ensure_sales_setup()
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": "عميل الكانبان",
				"first_name": "عميل",
				"mobile_no": "01055556666",
			}
		).insert(ignore_permissions=True)
		opp = make_opportunity(lead.name)
		opp.insert(ignore_permissions=True)
		self.assertEqual(opp.pipeline_stage, "جديد")
		self.assertTrue(frappe.get_meta("Opportunity").track_changes, "track changes is off on Opportunity")
		opp.pipeline_stage = "تسعير"
		opp.save(ignore_permissions=True)
		versions = frappe.get_all(
			"Version", filters={"ref_doctype": "Opportunity", "docname": opp.name}, pluck="data"
		)
		self.assertTrue(any("pipeline_stage" in v for v in versions))
		self.assertTrue(frappe.db.exists("Kanban Board", sales.KANBAN_BOARD))
