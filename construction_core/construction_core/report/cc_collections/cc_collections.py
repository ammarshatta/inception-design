"""التحصيل (phase 17). The numbers come from `construction_core.analytics.collections`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "customer", "label": "العميل", "fieldtype": "Link", "width": 150, "options": "Customer"},
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "outstanding", "label": "المتبقي", "fieldtype": "Currency", "width": 120},
	{"fieldname": "overdue", "label": "متأخر", "fieldtype": "Currency", "width": 120},
	{"fieldname": "0-30", "label": "0-30 يوم", "fieldtype": "Currency", "width": 120},
	{"fieldname": "31-60", "label": "31-60", "fieldtype": "Currency", "width": 120},
	{"fieldname": "61-90", "label": "61-90", "fieldtype": "Currency", "width": 120},
	{"fieldname": "90+", "label": "أكتر من 90", "fieldtype": "Currency", "width": 120},
	{"fieldname": "next_30", "label": "مستحق خلال 30 يوم", "fieldtype": "Currency", "width": 120},
	{"fieldname": "next_60", "label": "خلال 60 يوم", "fieldtype": "Currency", "width": 120},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.collections(filters)
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	return columns, rows
