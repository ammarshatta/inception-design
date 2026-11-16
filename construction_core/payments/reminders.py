"""Polite milestone reminders (phase 15, task 5).

Daily: for every unpaid milestone with a due date, send on day −3, 0, +7 and +14 relative to the
due date, once each (Payment Reminder Log makes it idempotent, so a re-run or a missed day never
double-sends; a missed day is not caught up, so a client never gets two at once).

Channels: a portal notification always; an email when an outgoing account exists; and a wa.me
link stored in the log for the admin to send by hand ("Payment Reminders" list).
Formal overdue letters use ERPNext Dunning on the Sales Invoice.
"""

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import date_diff, flt, get_url, getdate, nowdate

OFFSETS = (-3, 0, 7, 14)


def _text(s, offset: int, values: dict) -> str:
	if offset < 0:
		template = s.reminder_before_text
	elif offset == 0:
		template = s.reminder_due_text
	else:
		template = s.reminder_overdue_text
	template = template or _("تذكير بدفعة «{label}» بقيمة {amount} ج.م.")
	try:
		return template.format(**values)
	except KeyError, IndexError, ValueError:
		return template


def _clients(project: str) -> list[str]:
	from construction_core.notifications import _clients as clients

	return clients(project)


def send_due_reminders(today=None) -> list[str]:
	s = frappe.get_cached_doc("Inceptiondesign Settings")
	if not s.enable_payment_reminders:
		return []
	today = getdate(today or nowdate())
	sent = []
	for m in frappe.get_all(
		"Payment Milestone",
		filters={"status": ["in", ["Due", "Invoiced"]], "due_date": ["is", "set"]},
		fields=["name", "project", "label", "amount", "due_date", "sales_invoice"],
	):
		offset = date_diff(today, m.due_date)
		if offset not in OFFSETS:
			continue
		if frappe.db.exists("Payment Reminder Log", {"payment_milestone": m.name, "offset_days": offset}):
			continue
		amount = m.amount
		if m.sales_invoice and frappe.db.get_value("Sales Invoice", m.sales_invoice, "docstatus") == 1:
			amount = frappe.db.get_value("Sales Invoice", m.sales_invoice, "outstanding_amount")
		if flt(amount, 2) <= 0:
			continue
		link = get_url(f"/portal/c/{m.project}/payments")
		for user in _clients(m.project) or [None]:
			full_name = frappe.utils.get_fullname(user) if user else ""
			values = {
				"client": full_name,
				"label": m.label,
				"amount": f"{flt(amount, 2):,.2f}",
				"due_date": frappe.utils.formatdate(m.due_date),
				"days": max(offset, 0),
				"link": link,
			}
			text = _text(s, offset, values)
			channels = []
			if user:
				from construction_core.notifications import _notify

				_notify([user], text[:140], "Payment Milestone", m.name)
				channels.append("portal")
				email = frappe.db.get_value("User", user, "email")
				if (
					email
					and not email.endswith(".invalid")
					and frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1})
				):
					frappe.sendmail(
						recipients=[email],
						subject=_("تذكير بدفعة: {0}").format(m.label),
						message=text,
						now=False,
					)
					channels.append("email")
			mobile = frappe.db.get_value("User", user, "mobile_no") if user else None
			wa = ""
			if mobile and mobile.startswith("01"):
				wa = f"https://wa.me/20{mobile[1:]}?text=" + quote(text)
			log = frappe.get_doc(
				{
					"doctype": "Payment Reminder Log",
					"payment_milestone": m.name,
					"project": m.project,
					"offset_days": offset,
					"sent_on": today,
					"recipient": user,
					"channels": ",".join(channels),
					"whatsapp_url": wa,
				}
			)
			log.insert(ignore_permissions=True)
			sent.append(log.name)
	return sent


@frappe.whitelist()
def todays_whatsapp(on_date=None) -> list[dict]:
	"""The admin's list of wa.me links for today's reminders."""
	from construction_core.permissions import has_full_access

	if not has_full_access():
		frappe.throw(_("Only the office admin"), frappe.PermissionError)
	return frappe.get_all(
		"Payment Reminder Log",
		filters={"sent_on": getdate(on_date or nowdate()), "whatsapp_url": ["is", "set"]},
		fields=["payment_milestone", "project", "recipient", "offset_days", "whatsapp_url"],
	)
