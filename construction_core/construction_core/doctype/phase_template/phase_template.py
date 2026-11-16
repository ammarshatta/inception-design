# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PhaseTemplate(Document):
	def validate(self):
		for row in self.stages:
			if flt(row.weight) < 0:
				frappe.throw(_("Row {0}: weight cannot be negative").format(row.idx))
		self.total_weight = flt(sum(flt(row.weight) for row in self.stages), 2)
		if self.total_weight != 100:
			frappe.msgprint(
				_("Stage weights add up to {0}, not 100.").format(self.total_weight),
				indicator="orange",
				alert=True,
			)


def checklist_lines(text: str | None) -> list[str]:
	"""One checklist item per non-empty line."""
	return [line.strip() for line in (text or "").splitlines() if line.strip()]
