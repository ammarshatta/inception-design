# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from construction_core.costing import engine
from construction_core.costing.engine import round2


class ChangeOrder(Document):
	def validate(self):
		before = self.get_doc_before_save()
		if before and not self.flags.allow_status and self.status != before.status:
			frappe.throw(
				_("The status changes only through the change order actions"), frappe.PermissionError
			)
		if (
			before
			and before.status in ("Sent to Client", "Rejected", "Cancelled")
			and not self.flags.allow_status
		):
			frappe.throw(_("This change order can no longer be edited"), frappe.PermissionError)
		self.recalculate()

	def recalculate(self):
		"""Priced with the costing engine; removals are negative quantities. Never typed in."""
		on_date = frappe.utils.nowdate()
		parts = [engine.line_parts(line, on_date) for line in self.lines]
		res = engine.compute(parts, self.overhead_pct, self.profit_pct, engine.tax_rate(self.taxes_template))
		for line, total, p in zip(self.lines, res["line_totals"], parts, strict=True):
			line.line_total = total
			line.material_part = round2(p["Material"])
			line.labor_part = round2(p["Labor"])
			line.equipment_part = round2(p["Equipment"])
			line.other_part = round2(p["Other"])
		self.cost_subtotal = round2(res["subtotal"])
		self.tax_amount = round2(res["tax"])
		self.cost_difference = res["grand_total"]

	def before_submit(self):
		if self.status != "Approved":
			frappe.throw(_("A change order is approved by the client's signature"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def on_trash(self):
		frappe.throw(_("Change orders keep their history; cancel instead"))
