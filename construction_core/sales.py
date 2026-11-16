"""Sales pipeline, price library and estimate actions (phase 7)."""

import csv
import io

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate, nowdate

from construction_core.costing.engine import BUYING_PRICE_LIST, D, ensure_price_list, round2

PIPELINE_STAGES = ("جديد", "معاينة", "تسعير", "عرض مرسل", "تفاوض", "اتكسب", "اتخسر")
KANBAN_BOARD = "مسار المبيعات"
QUOTATION_ITEM = "بنود تشطيب"
SALES_ROLES = {"System Manager", "Construction Admin", "Construction Sales"}


def _require_sales():
	if not set(frappe.get_roles()) & SALES_ROLES:
		frappe.throw(_("Only sales or the office admin can do this"), frappe.PermissionError)


def ensure_sales_setup():
	if not frappe.is_setup_complete():
		return
	ensure_price_list()
	if not frappe.db.exists("Kanban Board", KANBAN_BOARD) and frappe.get_meta("Opportunity").has_field(
		"pipeline_stage"
	):
		frappe.get_doc(
			{
				"doctype": "Kanban Board",
				"kanban_board_name": KANBAN_BOARD,
				"reference_doctype": "Opportunity",
				"field_name": "pipeline_stage",
				"private": 0,
				"columns": [
					{"column_name": s, "status": "Active", "indicator": "Gray"} for s in PIPELINE_STAGES
				],
			}
		).insert(ignore_permissions=True)


# --- Price library --------------------------------------------------------------------


def item_price_on_trash(doc, method=None):
	"""Old prices are never deleted; a new dated price supersedes them (story P07-02)."""
	if doc.price_list == BUYING_PRICE_LIST:
		frappe.throw(_("Prices are kept for history. Add a new price with a later date instead."))


def labor_rate_on_trash(doc, method=None):
	frappe.throw(_("Prices are kept for history. Add a new price with a later date instead."))


PRICE_COLUMNS = ["type", "item_or_labor", "uom", "rate", "valid_from", "governorate", "source", "source_ref"]


@frappe.whitelist()
def price_import_template():
	"""A CSV template for bulk price import."""
	from werkzeug.wrappers import Response

	out = io.StringIO()
	w = csv.writer(out)
	w.writerow(PRICE_COLUMNS)
	w.writerow(["material", "سيراميك 60×60", "Nos", "350", nowdate(), "", "Quotation", "عرض سعر رقم 12"])
	w.writerow(["labor", "مصنعية سيراميك", "Nos", "120", nowdate(), "القاهرة", "Market survey", ""])
	resp = Response("﻿" + out.getvalue(), content_type="text/csv; charset=utf-8")
	resp.headers["Content-Disposition"] = 'attachment; filename="price-import-template.csv"'
	return resp


def _read_rows(file_url: str) -> list[dict]:
	file = frappe.get_doc("File", {"file_url": file_url})
	content = file.get_content()
	if file.file_name.lower().endswith(".xlsx"):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

		rows = read_xlsx_file_from_attached_file(fcontent=content)
	else:
		text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
		rows = list(csv.reader(io.StringIO(text)))
	header = [cstr(h).strip() for h in rows[0]]
	return [dict(zip(header, r, strict=False)) for r in rows[1:] if any(cstr(c).strip() for c in r)]


@frappe.whitelist(methods=["POST"])
def import_prices(file_url: str) -> dict:
	"""Creates new dated prices; reports errors per row (story P07-07)."""
	_require_sales()
	ensure_price_list()
	created, errors = 0, []
	for i, row in enumerate(_read_rows(file_url), start=2):
		try:
			kind = cstr(row.get("type")).strip().lower()
			name = cstr(row.get("item_or_labor")).strip()
			rate = D(cstr(row.get("rate")).strip() or "x")
			valid_from = getdate(row.get("valid_from"))
			source = cstr(row.get("source")).strip() or "Market survey"
			if kind == "material":
				if not frappe.db.exists("Item", name):
					raise ValueError(_("Item {0} not found").format(name))
				frappe.get_doc(
					{
						"doctype": "Item Price",
						"item_code": name,
						"price_list": BUYING_PRICE_LIST,
						"price_list_rate": rate,
						"valid_from": valid_from,
						"uom": cstr(row.get("uom")).strip() or None,
						"price_source": source,
						"source_ref": cstr(row.get("source_ref")),
					}
				).insert()
			elif kind == "labor":
				frappe.get_doc(
					{
						"doctype": "Labor Rate",
						"labor_type": name,
						"uom": cstr(row.get("uom")).strip() or "Nos",
						"rate": rate,
						"valid_from": valid_from,
						"governorate": cstr(row.get("governorate")).strip(),
						"source": source,
						"source_ref": cstr(row.get("source_ref")),
					}
				).insert()
			else:
				raise ValueError(_("type must be material or labor"))
			created += 1
		except Exception as e:
			frappe.clear_last_message()
			errors.append({"row": i, "error": cstr(e) or e.__class__.__name__})
	return {"created": created, "errors": errors}


# --- Estimates ------------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def estimate_from_design(design: str, customer: str | None = None, lead: str | None = None) -> str:
	"""A draft estimate whose sections are the design's stages (one placeholder line each)."""
	_require_sales()
	d = frappe.get_doc("Design Template", design)
	stages = []
	if d.phase_template:
		stages = [r.stage_name for r in frappe.get_doc("Phase Template", d.phase_template).stages]
	est = frappe.get_doc(
		{
			"doctype": "Estimate",
			"title": d.title,
			"customer": customer,
			"lead": lead,
			"design_template": design,
			"estimate_date": nowdate(),
			"lines": [
				{"section": s, "line_type": "Other", "description": s, "qty": 1, "unit_cost": 0}
				for s in stages
			],
		}
	)
	est.insert()
	return est.name


@frappe.whitelist(methods=["POST"])
def revise(estimate: str) -> str:
	"""Approved estimate → revision N+1 (draft); the old one becomes Superseded."""
	_require_sales()
	old = frappe.get_doc("Estimate", estimate)
	if old.docstatus != 1 or old.status != "Approved":
		frappe.throw(_("Only an approved estimate can be revised"))
	new = frappe.copy_doc(old)
	new.revision = cint(old.revision) + 1
	new.previous_revision = old.name
	new.status = "Draft"
	new.quotation = None
	new.estimate_date = nowdate()
	new.insert()
	old.db_set("status", "Superseded")
	return new.name


def _line_key(line) -> tuple:
	ref = line.get("assembly") or line.get("item") or line.get("labor_type") or line.get("description")
	return (cstr(line.get("section")), cstr(line.get("line_type")), cstr(ref))


@frappe.whitelist()
def compare_revisions(a: str, b: str) -> dict:
	"""Lines added, removed and changed from revision `a` to revision `b`, with money differences."""
	old = {_line_key(r): r for r in frappe.get_doc("Estimate", a).lines}
	new = {_line_key(r): r for r in frappe.get_doc("Estimate", b).lines}

	def row(line):
		return {
			"section": line.section,
			"type": line.line_type,
			"ref": _line_key(line)[2],
			"qty": line.qty,
			"unit_cost": line.unit_cost,
			"line_total": line.line_total,
		}

	added = [row(new[k]) for k in new if k not in old]
	removed = [row(old[k]) for k in old if k not in new]
	changed = []
	for k in new:
		if k in old:
			o, n = old[k], new[k]
			if D(o.qty) != D(n.qty) or D(o.unit_cost) != D(n.unit_cost) or D(o.line_total) != D(n.line_total):
				changed.append(
					{
						**row(n),
						"old_qty": o.qty,
						"old_unit_cost": o.unit_cost,
						"old_line_total": o.line_total,
						"difference": round2(D(n.line_total) - D(o.line_total)),
					}
				)
	total_a = D(frappe.db.get_value("Estimate", a, "grand_total"))
	total_b = D(frappe.db.get_value("Estimate", b, "grand_total"))
	return {
		"added": added,
		"removed": removed,
		"changed": changed,
		"added_total": round2(sum((D(r["line_total"]) for r in added), D(0))),
		"removed_total": round2(sum((D(r["line_total"]) for r in removed), D(0))),
		"grand_total_difference": round2(total_b - total_a),
	}


def _ensure_quotation_item() -> str:
	from construction_core.money import SERVICE_ITEM_GROUP, ensure_item_groups

	ensure_item_groups()
	if not frappe.db.exists("Item", QUOTATION_ITEM):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": QUOTATION_ITEM,
				"item_name": QUOTATION_ITEM,
				"item_group": SERVICE_ITEM_GROUP,
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		).insert(ignore_permissions=True)
	return QUOTATION_ITEM


@frappe.whitelist(methods=["POST"])
def make_quotation(estimate: str) -> str:
	"""Approved estimate → ERPNext Quotation, one line per section (story P07-06)."""
	_require_sales()
	est = frappe.get_doc("Estimate", estimate)
	if est.docstatus != 1 or est.status != "Approved":
		frappe.throw(_("Approve the estimate first"))
	if est.quotation:
		return est.quotation
	item = _ensure_quotation_item()
	party_type, party = ("Customer", est.customer) if est.customer else ("Lead", est.lead)
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	q = frappe.get_doc(
		{
			"doctype": "Quotation",
			"quotation_to": party_type,
			"party_name": party,
			"company": company,
			"transaction_date": nowdate(),
			"estimate": est.name,
			"opportunity": est.opportunity,
			"taxes_and_charges": est.taxes_template,
			"items": [
				{"item_code": item, "item_name": section, "description": section, "qty": 1, "rate": amount}
				for section, amount in est.section_totals().items()
			],
		}
	)
	q.insert()
	est.db_set("quotation", q.name)
	return q.name


@frappe.whitelist(methods=["POST"])
def add_followup(opportunity: str, date: str, note: str | None = None) -> str:
	"""A follow-up reminder: an ERPNext ToDo with a due date on the opportunity."""
	_require_sales()
	from frappe.desk.form.assign_to import add

	add(
		{
			"assign_to": [frappe.session.user],
			"doctype": "Opportunity",
			"name": opportunity,
			"date": date,
			"description": note or _("متابعة"),
		}
	)
	return frappe.db.get_value(
		"ToDo", {"reference_type": "Opportunity", "reference_name": opportunity, "status": "Open"}, "name"
	)
