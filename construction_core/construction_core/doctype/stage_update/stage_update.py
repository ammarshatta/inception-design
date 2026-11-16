# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class StageUpdate(Document):
	def validate(self):
		stage_project = frappe.db.get_value("Project Stage", self.project_stage, "project")
		if stage_project != self.project:
			frappe.throw(_("The stage does not belong to this project"))
		if self.progress_after is not None and not 0 <= flt(self.progress_after) <= 100:
			frappe.throw(_("Progress must be between 0 and 100"))

	def after_insert(self):
		"""For a Manual stage, a progress_after above 0 becomes the stage's progress."""
		if flt(self.progress_after) <= 0:
			return
		stage = frappe.get_doc("Project Stage", self.project_stage)
		if stage.progress_mode != "Manual":
			return
		stage.progress = flt(self.progress_after)
		stage.flags.ignore_permissions = True
		stage.save()
