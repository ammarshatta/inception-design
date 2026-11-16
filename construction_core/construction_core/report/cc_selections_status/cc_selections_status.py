"""حالة الاختيارات (phase 17). The numbers come from `construction_core.analytics.selections_status`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "project_name", "label": "الاسم", "fieldtype": "Data", "width": 180},
	{"fieldname": "open", "label": "مفتوحة", "fieldtype": "Int", "width": 80},
	{"fieldname": "overdue", "label": "متأخرة", "fieldtype": "Int", "width": 80},
	{"fieldname": "awaiting", "label": "مستنية توقيع", "fieldtype": "Int", "width": 100},
	{"fieldname": "approved", "label": "معتمدة", "fieldtype": "Int", "width": 80},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.selections_status(filters)
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	return columns, rows
