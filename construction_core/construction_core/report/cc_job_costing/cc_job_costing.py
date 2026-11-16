"""تكاليف المشروع (phase 17). The numbers come from `construction_core.analytics.job_costing`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "stage_name", "label": "المرحلة", "fieldtype": "Data", "width": 150},
	{"fieldname": "type", "label": "النوع", "fieldtype": "Data", "width": 110},
	{"fieldname": "budget", "label": "الميزانية", "fieldtype": "Currency", "width": 120},
	{"fieldname": "committed", "label": "ملتزم بيه", "fieldtype": "Currency", "width": 120},
	{"fieldname": "actual", "label": "الفعلي", "fieldtype": "Currency", "width": 120},
	{"fieldname": "remaining", "label": "المتبقي", "fieldtype": "Currency", "width": 120},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.job_costing(filters)
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	return columns, rows
