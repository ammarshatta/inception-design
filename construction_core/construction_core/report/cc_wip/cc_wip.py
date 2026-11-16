"""أعمال تحت التنفيذ (phase 17). The numbers come from `construction_core.analytics.wip`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "project_name", "label": "الاسم", "fieldtype": "Data", "width": 180},
	{"fieldname": "contract", "label": "قيمة العقد", "fieldtype": "Currency", "width": 120},
	{"fieldname": "complete", "label": "الإنجاز %", "fieldtype": "Percent", "width": 90},
	{"fieldname": "earned", "label": "القيمة المكتسبة", "fieldtype": "Currency", "width": 120},
	{"fieldname": "billed", "label": "المفوتر", "fieldtype": "Currency", "width": 120},
	{"fieldname": "over_under", "label": "فوترة زيادة/ناقص", "fieldtype": "Currency", "width": 120},
	{"fieldname": "cost", "label": "التكلفة لحد النهارده", "fieldtype": "Currency", "width": 120},
	{"fieldname": "eac", "label": "التكلفة المتوقعة", "fieldtype": "Currency", "width": 120},
	{"fieldname": "margin", "label": "الهامش المتوقع", "fieldtype": "Currency", "width": 120},
	{"fieldname": "margin_pct", "label": "الهامش %", "fieldtype": "Percent", "width": 90},
	{"fieldname": "count", "label": "عدد", "fieldtype": "Int", "width": 60},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.wip(filters)
	for row in rows:
		row["count"] = 1
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	chart = (
		{
			"type": "bar",
			"data": {
				"labels": [r["project_name"] or r["project"] for r in rows[:15]],
				"datasets": [
					{"name": _("المكتسبة"), "values": [r["earned"] for r in rows[:15]]},
					{"name": _("المفوتر"), "values": [r["billed"] for r in rows[:15]]},
				],
			},
		}
		if rows
		else None
	)
	return columns, rows, None, chart
