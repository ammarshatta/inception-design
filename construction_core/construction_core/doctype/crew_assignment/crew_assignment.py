# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CrewAssignment(Document):
	def validate(self):
		from construction_core.scheduling import overlapping

		if not self.crew and not self.supplier:
			frappe.throw(_("Choose a crew or a subcontractor"))
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("The end date is before the start date"))
		project_name = frappe.db.get_value("Project", self.project, "project_name")
		self.title = f"{self.crew or self.supplier} · {project_name}"
		conflicts = overlapping(self) if self.status != "Cancelled" else []
		if conflicts:
			names = ", ".join(
				f"{frappe.db.get_value('Project', c.project, 'project_name')} ({c.from_date} → {c.to_date})"
				for c in conflicts
			)
			self.conflict_note = names
			# A warning, not a block: the admin may override, and the override is logged.
			frappe.msgprint(
				_("تعارض: نفس الفريق متسجل في {0}").format(names),
				title=_("تعارض في الجدول"),
				indicator="orange",
			)
			self.flags.conflict_override = True
		else:
			self.conflict_note = None

	def on_update(self):
		if self.flags.conflict_override:
			self.add_comment("Comment", _("اتحفظ رغم التعارض مع: {0}").format(self.conflict_note))
