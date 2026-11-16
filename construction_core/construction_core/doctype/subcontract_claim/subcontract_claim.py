# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from construction_core import subcontracts
from construction_core.permissions import has_full_access


class SubcontractClaim(Document):
	def validate(self):
		sub = frappe.get_doc("Subcontract", self.subcontract)
		if sub.docstatus != 1:
			frappe.throw(_("The subcontract is not signed yet"))
		self.project, self.supplier = sub.project, sub.supplier
		if not self.claim_no:
			self.claim_no = (
				cint(
					frappe.db.sql(
						"select max(claim_no) from `tabSubcontract Claim` where subcontract=%s and docstatus < 2",
						self.subcontract,
					)[0][0]
				)
				+ 1
			)
		self.title = _("مستخلص {0}: {1}").format(self.claim_no, sub.title)
		if (
			self.admin_override
			and (self.is_new() or self.has_value_changed("admin_override"))
			and not has_full_access()
		):
			frappe.throw(
				_("Only the office admin can allow quantities above the contract"), frappe.PermissionError
			)
		result = subcontracts.compute_claim(
			sub,
			[{"subcontract_line": l.subcontract_line, "current_qty": l.current_qty} for l in self.lines],
			subcontracts.previous_quantities(self.subcontract, exclude=self.name),
			subcontracts.advance_recovered(self.subcontract, exclude=self.name),
		)
		if any(flt(l.current_qty) < 0 for l in self.lines):
			frappe.throw(_("Quantities cannot be negative"))
		self.set("lines", result["lines"])
		for f in ("gross", "retention_amount", "advance_recovery", "net_due"):
			self.set(f, flt(result[f], 2))
		self.flags.over = result["over"]
		if self.docstatus == 0:
			self.status = "Draft"

	def before_submit(self):
		if not has_full_access():
			frappe.throw(_("Only the office admin approves claims"), frappe.PermissionError)
		if self.flags.over:
			if not self.admin_override:
				frappe.throw(
					_("الكمية التراكمية أكبر من كمية العقد: {0}. محتاج موافقة المدير.").format(
						"، ".join(self.flags.over)
					)
				)
			self.add_comment(
				"Info",
				_("تجاوز كمية العقد بموافقة {0}: {1}").format(
					frappe.session.user, self.override_reason or ""
				),
			)
		if flt(self.gross) <= 0:
			frappe.throw(_("The claim has no work in it"))
		self.status = "Approved"
		self.approved_by = frappe.session.user

	def on_submit(self):
		from construction_core.utils import as_system

		with as_system():
			pi = subcontracts.make_claim_invoice(self)
		self.db_set("purchase_invoice", pi)

	def before_cancel(self):
		# the claim's own invoice is cancelled with it (below)
		self.ignore_linked_doctypes = ("Purchase Invoice",)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		if (
			self.purchase_invoice
			and frappe.db.get_value("Purchase Invoice", self.purchase_invoice, "docstatus") == 1
		):
			pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
			pi.flags.ignore_permissions = True
			pi.cancel()
