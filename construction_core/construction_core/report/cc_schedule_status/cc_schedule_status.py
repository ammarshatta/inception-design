"""المشاريع المتأخرة (phase 17). The numbers come from `construction_core.analytics.schedule_status`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "project_name", "label": "الاسم", "fieldtype": "Data", "width": 180},
	{"fieldname": "days_late", "label": "أيام التأخير", "fieldtype": "Int", "width": 100},
	{"fieldname": "stage", "label": "المرحلة المتأخرة", "fieldtype": "Data", "width": 150},
	{"fieldname": "planned_end", "label": "كان المفروض تخلص", "fieldtype": "Date", "width": 120},
	{"fieldname": "progress", "label": "إنجازها %", "fieldtype": "Percent", "width": 90},
	{"fieldname": "count", "label": "عدد", "fieldtype": "Int", "width": 60},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.schedule_status(filters)
	for row in rows:
		row["count"] = 1
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	return columns, rows
