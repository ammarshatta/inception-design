"""تجاوز الميزانية (phase 17). The numbers come from `construction_core.analytics.budget_variance`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "stage_name", "label": "المرحلة", "fieldtype": "Data", "width": 140},
	{"fieldname": "type", "label": "النوع", "fieldtype": "Data", "width": 100},
	{"fieldname": "budget", "label": "الميزانية", "fieldtype": "Currency", "width": 120},
	{"fieldname": "spent", "label": "فعلي + ملتزم", "fieldtype": "Currency", "width": 120},
	{"fieldname": "over", "label": "التجاوز", "fieldtype": "Currency", "width": 120},
	{"fieldname": "over_pct", "label": "التجاوز %", "fieldtype": "Percent", "width": 90},
	{"fieldname": "reasons", "label": "أوامر التغيير", "fieldtype": "Data", "width": 260},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.budget_variance(filters)
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	return columns, rows
