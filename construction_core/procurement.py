"""From needs to orders, and receiving on site (phase 13).

ERPNext does the purchasing itself: Material Request → Request for Quotation → Supplier
Quotation (ERPNext's "Supplier Quotation Comparison" report) → Purchase Order → Purchase
Receipt → Purchase Invoice. Every item row carries `project` and `project_stage`, and
ERPNext's mappers copy them along the chain (same field name on every item table).

We add:
- material requests generated from approved estimates and approved selections
- the engineer's on-site delivery confirmation with a photo of the delivery note
"""

import base64
import io
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from construction_core.costing.engine import D, round2
from construction_core.permissions import assert_project_access, has_full_access, is_client

PURCHASING_ROLES = {"System Manager", "Construction Admin", "Purchase User", "Purchase Manager"}
DEFAULT_LEAD_DAYS = 7


def _require_purchasing():
	if not (has_full_access() or PURCHASING_ROLES & set(frappe.get_roles())):
		frappe.throw(_("Only purchasing or the office admin can do this"), frappe.PermissionError)


# --- Needs ----------------------------------------------------------------------------


def project_needs(project: str) -> list[dict]:
	"""Material needs from the project's approved estimate(s) and approved selections.

	Each need: item, qty (with waste), uom, project_stage, source (a stable key, so a need is
	requested only once)."""
	stages = {
		r.stage_name: r.name
		for r in frappe.get_all("Project Stage", filters={"project": project}, fields=["name", "stage_name"])
	}
	needs = []
	for est in frappe.get_all("Estimate", filters={"project": project, "docstatus": 1}, pluck="name"):
		doc = frappe.get_doc("Estimate", est)
		for line in doc.lines:
			stage = stages.get(line.section)
			if line.line_type == "Material" and line.item:
				qty = D(line.qty) * (D(1) + D(line.waste_pct) / D(100))
				needs.append(
					{
						"item": line.item,
						"qty": qty,
						"uom": line.uom,
						"project_stage": stage,
						"source": f"Estimate Line:{line.name}",
					}
				)
			elif line.line_type == "Assembly" and line.assembly:
				for comp in frappe.get_doc("Assembly", line.assembly).items:
					if comp.line_type != "Material" or not comp.item:
						continue
					qty = (
						D(line.qty)
						* D(comp.qty_per_unit)
						* (D(1) + D(comp.waste_pct) / D(100))
						* (D(1) + D(line.waste_pct) / D(100))
					)
					needs.append(
						{
							"item": comp.item,
							"qty": qty,
							"uom": None,
							"project_stage": stage,
							"source": f"Estimate Line:{line.name}:{comp.name}",
						}
					)
	for sel in frappe.get_all(
		"Project Selection",
		filters={"project": project, "status": ["in", ["Approved", "Locked"]]},
		fields=["name", "chosen_option", "qty", "uom", "project_stage"],
	):
		item = sel.chosen_option and frappe.db.get_value("Selection Option", sel.chosen_option, "item")
		if item and flt(sel.qty) > 0:
			needs.append(
				{
					"item": item,
					"qty": D(sel.qty),
					"uom": sel.uom,
					"project_stage": sel.project_stage,
					"source": f"Project Selection:{sel.name}",
				}
			)
	return needs


def _already_requested(project: str) -> set:
	return set(
		frappe.db.sql_list(
			"""select mri.cc_source from `tabMaterial Request Item` mri
			join `tabMaterial Request` mr on mr.name = mri.parent
			where mr.docstatus < 2 and mri.project = %s and ifnull(mri.cc_source, '') != ''""",
			project,
		)
	)


def _needed_by(stage: str | None):
	today = getdate(nowdate())
	start = stage and frappe.db.get_value("Project Stage", stage, "planned_start")
	if start:
		return max(today, getdate(add_days(start, -2)))
	return getdate(add_days(today, DEFAULT_LEAD_DAYS))


@frappe.whitelist(methods=["POST"])
def make_material_requests(project: str) -> list[str]:
	"""One draft Material Request per stage for every need not requested yet."""
	_require_purchasing()
	assert_project_access(project)
	company = frappe.db.get_value("Project", project, "company")
	done = _already_requested(project)
	by_stage = defaultdict(list)
	for need in project_needs(project):
		if need["source"] not in done:
			by_stage[need["project_stage"] or ""].append(need)
	created = []
	for stage, needs in by_stage.items():
		needed_by = _needed_by(stage or None)
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": company,
				"transaction_date": nowdate(),
				"schedule_date": needed_by,
				"items": [
					{
						"item_code": n["item"],
						"qty": flt(round2(n["qty"]), 3),
						"uom": n["uom"] or frappe.db.get_value("Item", n["item"], "stock_uom"),
						"schedule_date": needed_by,
						"project": project,
						"project_stage": stage or None,
						"cc_source": n["source"],
					}
					for n in needs
				],
			}
		)
		mr.flags.ignore_permissions = True
		mr.insert()
		created.append(mr.name)
	return created


# --- Receiving on site ----------------------------------------------------------------


@frappe.whitelist()
def open_deliveries(project: str) -> list[dict]:
	"""Submitted purchase orders for this project that are not fully received yet."""
	if is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	assert_project_access(project)
	rows = frappe.db.sql(
		"""select po.name, po.supplier_name, po.schedule_date, po.per_received,
			poi.item_name, poi.qty, poi.received_qty, poi.uom, poi.project_stage
		from `tabPurchase Order` po join `tabPurchase Order Item` poi on poi.parent = po.name
		where po.docstatus = 1 and po.status not in ('Closed', 'On Hold', 'Completed')
			and poi.project = %s and poi.received_qty < poi.qty
		order by po.schedule_date asc, po.name, poi.idx""",
		project,
		as_dict=True,
	)
	orders = {}
	for r in rows:
		o = orders.setdefault(
			r.name,
			{"name": r.name, "supplier": r.supplier_name, "schedule_date": str(r.schedule_date), "items": []},
		)
		o["items"].append(
			{"item_name": r.item_name, "qty": flt(r.qty), "received_qty": flt(r.received_qty), "uom": r.uom}
		)
	return list(orders.values())


def _decode_photo(photo: str) -> bytes:
	if not photo:
		frappe.throw(_("صوّر إذن التسليم الأول"))
	data = photo.split(",", 1)[1] if photo.startswith("data:") else photo
	try:
		content = base64.b64decode(data, validate=True)
	except Exception:
		frappe.throw(_("This file is not a photo"))
	if len(content) > 8 * 1024 * 1024:
		frappe.throw(_("The photo is too large"))
	from PIL import Image

	try:
		with Image.open(io.BytesIO(content)) as img:
			img.verify()
	except Exception:
		frappe.throw(_("This file is not a photo"))
	from construction_core.media import reencode

	return reencode(content)  # ≤ 1600 px, no EXIF


@frappe.whitelist(methods=["POST"])
def confirm_delivery(purchase_order: str, photo: str, notes: str | None = None) -> str:
	"""The engineer confirms what arrived: a submitted Purchase Receipt for the open quantities,
	with the delivery-note photo attached (private)."""
	if is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	po = frappe.db.get_value("Purchase Order", purchase_order, ["docstatus", "name"], as_dict=True)
	if not po or po.docstatus != 1:
		frappe.throw(_("Purchase order not found"), frappe.PermissionError)
	projects = set(
		frappe.get_all(
			"Purchase Order Item", filters={"parent": purchase_order}, pluck="project", distinct=True
		)
	) - {None, ""}
	if not projects:
		frappe.throw(_("This purchase order is not linked to a project"))
	for p in projects:
		assert_project_access(p)  # never trust the order number from the browser
	content = _decode_photo(photo)
	user = frappe.session.user

	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	from construction_core.utils import as_system

	with as_system():
		pr = make_purchase_receipt(purchase_order)
		if not pr.items:
			frappe.throw(_("Everything on this order was already received"))
		pr.confirmed_on_site_by = user
		if notes:
			pr.remarks = notes[:1000]
		pr.insert()
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{pr.name}-delivery-note.jpg",
				"content": content,
				"is_private": 1,
				"attached_to_doctype": "Purchase Receipt",
				"attached_to_name": pr.name,
				"attached_to_field": "delivery_note_photo",
			}
		)
		f.insert()
		pr.db_set("delivery_note_photo", f.file_url)
		pr.reload()
		pr.submit()
	return pr.name
