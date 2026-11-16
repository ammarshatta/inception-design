"""Portal notifications and realtime (phase 4, tasks 3–4).

In-portal: Frappe `Notification Log` (which also emails, when an outgoing account
exists). Realtime: `publish_realtime(..., user=...)` to each member of the project,
so only people on the project receive it.
"""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

from construction_core.permissions import CLIENT_ROLE, ENGINEER_ROLE


def project_members(project: str) -> list[str]:
	return frappe.get_all("Project User", filters={"parenttype": "Project", "parent": project}, pluck="user")


def _clients(project: str) -> list[str]:
	return [
		u
		for u in project_members(project)
		if CLIENT_ROLE in frappe.get_roles(u) and ENGINEER_ROLE not in frappe.get_roles(u)
	]


def _notify(users: list[str], subject: str, doctype: str, name: str):
	users = [u for u in set(users) if u and u != frappe.session.user]
	if not users:
		return
	enqueue_create_notification(
		users,
		{
			"type": "Alert",
			"document_type": doctype,
			"document_name": name,
			"subject": subject,
			"from_user": frappe.session.user,
		},
	)


def stage_update_after_insert(doc, method=None):
	"""A new non-internal update notifies the clients. Internal updates notify nobody outside the team."""
	if doc.internal_only:
		return
	stage = frappe.db.get_value("Project Stage", doc.project_stage, "stage_name")
	_notify(_clients(doc.project), _("تحديث جديد في مرحلة {0}").format(stage), "Stage Update", doc.name)


def project_stage_on_update(doc, method=None):
	if doc.status == "Done" and doc.has_value_changed("status"):
		_notify(_clients(doc.project), _("خلصت مرحلة {0}").format(doc.stage_name), "Project Stage", doc.name)


def project_message_after_insert(doc, method=None):
	members = project_members(doc.project)
	if doc.kind == "Approval":
		subject = _("مطلوب موافقتك: {0}").format(doc.approval_title)
		_notify(_clients(doc.project), subject, "Project Message", doc.name)
	else:
		subject = _("رسالة جديدة من {0}").format(frappe.utils.get_fullname(doc.owner))
		_notify(members, subject, "Project Message", doc.name)
	for user in members:
		frappe.publish_realtime(
			"project_message",
			{"project": doc.project, "name": doc.name},
			user=user,
			after_commit=True,
		)


def payment_milestone_on_update(doc, method=None):
	if doc.status == "Due" and doc.has_value_changed("status"):
		subject = _("دفعة مستحقة: {0}").format(doc.label)
		_notify(_clients(doc.project), subject, "Payment Milestone", doc.name)
