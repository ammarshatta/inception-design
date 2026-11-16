# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PaymentMilestone(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero"))
		if self.project_stage:
			stage_project = frappe.db.get_value("Project Stage", self.project_stage, "project")
			if stage_project != self.project:
				frappe.throw(_("The stage does not belong to this project"))
