"""doc_events for ERPNext's Project (registered in hooks.py)."""

import frappe
from frappe.utils import flt

from construction_core.construction_core.doctype.phase_template.phase_template import checklist_lines
from construction_core.construction_core.doctype.project_stage.project_stage import update_project_progress


def has_outgoing_email() -> bool:
	return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}))


def before_validate(doc, method=None):
	"""ERPNext emails every new project user and fails when no outgoing email account exists.

	Until the office sets up email, new team rows are marked as welcomed; the office
	onboards clients with the Add Client dialog (set-password email or WhatsApp).
	"""
	if has_outgoing_email():
		return
	for row in doc.get("users") or []:
		if not row.welcome_email_sent:
			row.welcome_email_sent = 1


def after_insert(doc, method=None):
	"""Copy the template's stages and checklists into Project Stage records.

	The copy is a snapshot: later edits to the template never change this project.
	"""
	if not doc.get("phase_template"):
		return
	template = frappe.get_doc("Phase Template", doc.phase_template)
	for row in template.stages:
		stage = frappe.get_doc(
			{
				"doctype": "Project Stage",
				"project": doc.name,
				"stage_name": row.stage_name,
				"weight": flt(row.weight),
				"sort_order": row.idx,
				"status": "Not Started",
				"progress_mode": "Auto",
				"checklist": [{"label": line} for line in checklist_lines(row.checklist_text)],
			}
		)
		stage.flags.ignore_permissions = True
		stage.insert()
	update_project_progress(doc.name)
