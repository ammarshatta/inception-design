# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SignatureRequest(Document):
	def validate(self):
		if self.is_new():
			return
		if not self.flags.allow_system_update:
			# Only the e-signature module changes requests (through its whitelisted actions).
			frappe.throw(_("Signature requests change only through their actions"), frappe.PermissionError)
		before = self.get_doc_before_save()
		if before and before.status == "Signed":
			# A signed request is frozen; the one allowed write stores the signed PDF and its hash.
			allowed = {"signed_pdf", "signed_pdf_sha256", "modified", "modified_by"}
			if not self.flags.final_write or before.signed_pdf:
				frappe.throw(_("A signed document cannot be changed"), frappe.PermissionError)
			for field in self.meta.get_valid_columns():
				if field not in allowed and self.get(field) != before.get(field):
					frappe.throw(_("A signed document cannot be changed"), frappe.PermissionError)

	def on_trash(self):
		if self.status == "Signed":
			frappe.throw(_("A signed document cannot be deleted"), frappe.PermissionError)
