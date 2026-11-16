# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# The only fields a client may change on an Approval addressed to their project.
CLIENT_ANSWER_FIELDS = frozenset({"approval_status", "answer_note"})
# Fields the system sets when the answer is saved.
SYSTEM_ANSWER_FIELDS = frozenset({"answered_on", "answered_by"})
IGNORED_FIELDS = frozenset(
	{"modified", "modified_by", "idx", "_comments", "_assign", "_liked_by", "_user_tags", "_seen"}
)


class ProjectMessage(Document):
	def validate(self):
		from construction_core.permissions import is_client

		before = self.get_doc_before_save()
		if before and before.kind == "Approval" and before.approval_status not in (None, "", "Pending"):
			frappe.throw(
				_("This approval was already answered and cannot be changed"), frappe.PermissionError
			)

		if self.kind == "Approval":
			if not self.approval_title:
				frappe.throw(_("An approval needs a title"))
			if not self.approval_status:
				self.approval_status = "Pending"
		else:
			self.approval_status = None

		client = is_client()
		if self.is_new():
			if client and self.kind != "Text":
				frappe.throw(_("Clients can only send text messages"), frappe.PermissionError)
			if self.kind == "Approval" and self.approval_status != "Pending":
				frappe.throw(_("A new approval must start as Pending"))
			return

		if client:
			self.validate_client_edit(before)

		if before and before.approval_status == "Pending" and self.approval_status != "Pending":
			self.answered_on = now_datetime()
			self.answered_by = frappe.session.user

	def validate_client_edit(self, before):
		if self.kind != "Approval" or before.kind != "Approval":
			frappe.throw(_("Clients can only answer approvals"), frappe.PermissionError)
		for field in self.meta.get_valid_columns():
			if field in CLIENT_ANSWER_FIELDS or field in SYSTEM_ANSWER_FIELDS or field in IGNORED_FIELDS:
				continue
			if self.get(field) != before.get(field):
				frappe.throw(_("Clients can only change the answer of an approval"), frappe.PermissionError)

	def on_trash(self):
		if self.kind == "Approval" and self.approval_status not in (None, "", "Pending"):
			frappe.throw(_("An answered approval cannot be deleted"), frappe.PermissionError)
