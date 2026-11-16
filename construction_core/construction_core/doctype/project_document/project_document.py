# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class ProjectDocument(Document):
	def validate(self):
		before = self.get_doc_before_save()
		if before:
			old = {v.name: (cint(v.version_no), v.file, v.sha256) for v in before.versions}
			new = {v.name: (cint(v.version_no), v.file, v.sha256) for v in self.versions}
			for name, row in old.items():
				if new.get(name) != row:
					frappe.throw(_("Old versions are kept as they are: upload a new version instead"))
		if not self.versions:
			frappe.throw(_("Upload the file"))
		for v in self.versions:
			if not cint(v.version_no):
				frappe.throw(_("Upload new versions with the upload button"))
		latest = max(self.versions, key=lambda v: cint(v.version_no))
		self.current_version = cint(latest.version_no)
		self.current_file = latest.file

	def on_trash(self):
		if self.signature_request:
			frappe.throw(_("A signed contract cannot be deleted"), frappe.PermissionError)
