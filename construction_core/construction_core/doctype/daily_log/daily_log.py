# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class DailyLog(Document):
	def validate(self):
		other = frappe.db.get_value(
			"Daily Log",
			{"project": self.project, "log_date": self.log_date, "name": ["!=", self.name or ""]},
			"name",
		)
		if other:
			frappe.throw(_("There is already a daily log for this project on this day: {0}").format(other))
		if not self.author:
			self.author = frappe.session.user
		self.title = f"{frappe.db.get_value('Project', self.project, 'project_name')} · {self.log_date}"
