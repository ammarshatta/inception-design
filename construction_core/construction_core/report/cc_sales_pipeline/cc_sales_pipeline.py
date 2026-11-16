"""مسار المبيعات (phase 17): opportunities by stage, conversion, loss reasons, lead source."""

import frappe
from frappe import _

from construction_core import analytics


def execute(filters=None):
	filters = frappe._dict(filters or {})
	p = analytics.pipeline(filters)
	columns = [
		{"fieldname": "section", "label": _("القسم"), "fieldtype": "Data", "width": 140},
		{"fieldname": "label", "label": _("البند"), "fieldtype": "Data", "width": 200},
		{"fieldname": "count", "label": _("العدد"), "fieldtype": "Int", "width": 80},
		{"fieldname": "value", "label": _("القيمة"), "fieldtype": "Currency", "width": 140},
	]
	rows = [
		{"section": _("المراحل"), "label": s["stage"], "count": s["count"], "value": s["value"]}
		for s in p["stages"]
	]
	rows += [
		{"section": _("النتيجة"), "label": _("كسبنا"), "count": p["won"]},
		{"section": _("النتيجة"), "label": _("خسرنا"), "count": p["lost"]},
		{"section": _("النتيجة"), "label": _("نسبة التحويل %"), "value": p["conversion"]},
		{"section": _("النتيجة"), "label": _("متوسط قيمة التسعير"), "value": p["avg_estimate"]},
	]
	rows += [
		{"section": _("أسباب الخسارة"), "label": r["reason"], "count": r["count"]} for r in p["lost_reasons"]
	]
	rows += [{"section": _("مصدر العميل"), "label": r["source"], "count": r["count"]} for r in p["sources"]]
	chart = {
		"type": "bar",
		"data": {
			"labels": [s["stage"] for s in p["stages"]],
			"datasets": [{"name": _("العدد"), "values": [s["count"] for s in p["stages"]]}],
		},
	}
	return columns, rows, None, chart
