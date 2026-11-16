"""العمالة (phase 17). The numbers come from `construction_core.analytics.labor`."""

import frappe
from frappe import _

from construction_core import analytics

COLUMNS = [
	{"fieldname": "project", "label": "المشروع", "fieldtype": "Link", "width": 130, "options": "Project"},
	{"fieldname": "crew", "label": "الفريق", "fieldtype": "Link", "width": 120, "options": "Crew"},
	{"fieldname": "employee", "label": "الموظف", "fieldtype": "Link", "width": 120, "options": "Employee"},
	{"fieldname": "employee_name", "label": "الاسم", "fieldtype": "Data", "width": 150},
	{"fieldname": "hours", "label": "الساعات", "fieldtype": "Float", "width": 80},
	{"fieldname": "overtime", "label": "ساعات إضافي", "fieldtype": "Float", "width": 90},
	{"fieldname": "cost", "label": "التكلفة", "fieldtype": "Currency", "width": 120},
	{"fieldname": "flagged", "label": "حضور برة الموقع", "fieldtype": "Int", "width": 110},
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = analytics.labor(filters)
	columns = [{**c, "label": _(c["label"])} for c in COLUMNS]
	return columns, rows
