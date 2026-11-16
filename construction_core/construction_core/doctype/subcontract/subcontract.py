# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from construction_core.costing.engine import D, round2


class Subcontract(Document):
	def validate(self):
		total = D(0)
		for line in self.lines:
			if flt(line.qty) <= 0 or flt(line.rate) < 0:
				frappe.throw(_("Row {0}: quantity must be above 0 and rate not negative").format(line.idx))
			if (
				line.project_stage
				and frappe.db.get_value("Project Stage", line.project_stage, "project") != self.project
			):
				frappe.throw(_("Row {0}: the stage belongs to another project").format(line.idx))
			line.amount = flt(round2(D(line.qty) * D(line.rate)), 2)
			total += D(line.amount)
		self.contract_value = flt(round2(total), 2)
		if not 0 <= flt(self.retention_pct) <= 100:
			frappe.throw(_("Retention must be between 0 and 100%"))
		if flt(self.advance_amount) < 0 or flt(self.advance_amount) > flt(self.contract_value):
			frappe.throw(_("The advance must be between 0 and the contract value"))
		if self.docstatus == 0 and self.status not in ("Draft", "Awaiting Signature"):
			self.status = "Draft"

	def before_submit(self):
		if not self.flags.signed:
			frappe.throw(_("A subcontract becomes active only when the subcontractor signs it"))
		self.status = "Active"

	def on_cancel(self):
		if frappe.db.exists("Subcontract Claim", {"subcontract": self.name, "docstatus": 1}):
			frappe.throw(_("Cancel the approved claims first"))
		self.db_set("status", "Cancelled")
