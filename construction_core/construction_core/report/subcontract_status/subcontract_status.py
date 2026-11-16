"""حالة عقود الباطن (phase 13): value, claimed, retention held, advance recovered, paid."""

import frappe
from frappe import _

from construction_core.subcontracts import subcontract_status


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"fieldname": "name",
			"label": _("العقد"),
			"fieldtype": "Link",
			"options": "Subcontract",
			"width": 120,
		},
		{"fieldname": "title", "label": _("العنوان"), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "supplier",
			"label": _("المقاول"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{
			"fieldname": "project",
			"label": _("المشروع"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 150,
		},
		{"fieldname": "status", "label": _("الحالة"), "fieldtype": "Data", "width": 90},
		{"fieldname": "contract_value", "label": _("قيمة العقد"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "claimed", "label": _("المستخلص"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "retention", "label": _("المحتجز"), "fieldtype": "Currency", "width": 120},
		{
			"fieldname": "advance_recovered",
			"label": _("المسترد من المقدم"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{"fieldname": "paid", "label": _("المدفوع"), "fieldtype": "Currency", "width": 120},
	]
	return columns, subcontract_status(filters.get("project"))
