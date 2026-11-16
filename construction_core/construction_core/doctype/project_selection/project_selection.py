# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

CHOICE_FIELDS = {
	"status",
	"chosen_option",
	"chosen_unit_price",
	"price_difference",
	"signature_request",
	"change_order",
	"approved_on",
}
LOCKED = ("Awaiting Signature", "Approved", "Locked", "Superseded")


class ProjectSelection(Document):
	def validate(self):
		from construction_core.selections import price_difference

		self.title = " · ".join(x for x in (self.category, self.room_or_area) if x)
		if not self.uom:
			self.uom = frappe.db.get_value("Selection Category", self.category, "default_uom")
		if self.chosen_unit_price is not None and self.chosen_option:
			self.price_difference = price_difference(self.chosen_unit_price, self.qty, self.allowance_amount)
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if self.flags.allow_system_update:
			return
		# People (engineer, admin in the desk) may edit setup fields only while the selection is open,
		# and never the choice itself.
		if before.status in LOCKED:
			frappe.throw(_("This selection is locked"), frappe.PermissionError)
		for field in CHOICE_FIELDS:
			if self.get(field) != before.get(field):
				frappe.throw(_("The choice is made by the client in the portal"), frappe.PermissionError)
