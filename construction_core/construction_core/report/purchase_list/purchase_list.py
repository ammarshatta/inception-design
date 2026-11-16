"""قائمة الشراء: approved selections only, with item, quantity and date needed (phase 9)."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.project:
		frappe.throw(_("Choose a project"))
	frappe.get_doc("Project", filters.project).check_permission("read")
	columns = [
		{
			"fieldname": "selection",
			"label": _("الاختيار"),
			"fieldtype": "Link",
			"options": "Project Selection",
			"width": 120,
		},
		{"fieldname": "title", "label": _("المكان"), "fieldtype": "Data", "width": 200},
		{"fieldname": "option_name", "label": _("الاختيار"), "fieldtype": "Data", "width": 200},
		{"fieldname": "item", "label": _("الصنف"), "fieldtype": "Link", "options": "Item", "width": 160},
		{"fieldname": "qty", "label": _("الكمية"), "fieldtype": "Float", "width": 90},
		{"fieldname": "uom", "label": _("الوحدة"), "fieldtype": "Data", "width": 80},
		{"fieldname": "date_needed", "label": _("مطلوب قبل"), "fieldtype": "Date", "width": 110},
	]
	return columns, get_rows(filters.project)


def get_rows(project: str) -> list[dict]:
	rows = []
	for s in frappe.get_all(
		"Project Selection",
		filters={"project": project, "status": ["in", ["Approved", "Locked"]]},
		fields=["name", "title", "chosen_option", "qty", "uom", "due_date", "project_stage"],
		order_by="due_date asc",
	):
		opt = (
			frappe.db.get_value("Selection Option", s.chosen_option, ["option_name", "item"], as_dict=True)
			or {}
		)
		stage_start = (
			frappe.db.get_value("Project Stage", s.project_stage, "planned_start")
			if s.project_stage
			else None
		)
		rows.append(
			{
				"selection": s.name,
				"title": s.title,
				"option_name": opt.get("option_name"),
				"item": opt.get("item"),
				"qty": s.qty,
				"uom": s.uom,
				"date_needed": stage_start or s.due_date,
			}
		)
	return rows
