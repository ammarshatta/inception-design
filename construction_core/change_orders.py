"""Change orders (phase 10)."""

import frappe
from frappe import _
from frappe.utils import cstr, nowdate

from construction_core.costing.engine import D, round2
from construction_core.permissions import assert_project_access, has_full_access, is_client


def _team_and_admins(project: str) -> list[str]:
	from construction_core.notifications import project_members

	admins = frappe.get_all(
		"Has Role",
		filters={"role": "Construction Admin", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	members = [u for u in project_members(project) if "Construction Engineer" in frappe.get_roles(u)]
	return [u for u in set(admins + members) if u not in ("Administrator", "Guest")]


def _notify(users, subject, name):
	from construction_core.notifications import _notify as notify

	notify(users, subject, "Change Order", name)


@frappe.whitelist(methods=["POST"])
def request_change(
	project: str, description: str, photos: list | str | None = None, title: str | None = None
) -> str:
	"""Client ("اطلب تعديل") or engineer on site: a Draft with a description and photos."""
	assert_project_access(project)
	if not cstr(description).strip():
		frappe.throw(_("اكتب التعديل المطلوب"))
	photos = frappe.parse_json(photos) if isinstance(photos, str) else (photos or [])
	source = "Client Request" if is_client() else "Site Condition"
	co = frappe.get_doc(
		{
			"doctype": "Change Order",
			"project": project,
			"title": cstr(title).strip() or cstr(description).strip()[:80],
			"description": cstr(description).strip()[:4000],
			"source": source,
			"status": "Draft",
		}
	)
	co.flags.ignore_permissions = True
	co.insert()
	for url in photos[:10]:
		file = frappe.db.get_value(
			"File",
			{
				"file_url": url,
				"owner": frappe.session.user,
				"is_private": 1,
				"attached_to_name": ["is", "not set"],
			},
			"name",
		)
		if file:
			frappe.db.set_value(
				"File", file, {"attached_to_doctype": "Change Order", "attached_to_name": co.name}
			)
			co.append("photos", {"file": url})
	if co.photos:
		co.save(ignore_permissions=True)
	_notify(_team_and_admins(project), _("طلب تعديل جديد: {0}").format(co.title), co.name)
	return co.name


def draft_from_selection(selection_doc) -> str:
	"""A selection approved over its allowance creates a draft change order with the difference."""
	co = frappe.get_doc(
		{
			"doctype": "Change Order",
			"project": selection_doc.project,
			"project_stage": selection_doc.project_stage,
			"title": _("فرق اختيار: {0}").format(selection_doc.title),
			"source": "Selection",
			"project_selection": selection_doc.name,
			"overhead_pct": 0,
			"profit_pct": 0,
			"lines": [
				{
					"section": selection_doc.title,
					"line_type": "Other",
					"description": frappe.db.get_value(
						"Selection Option", selection_doc.chosen_option, "option_name"
					),
					"qty": 1,
					"unit_cost": selection_doc.price_difference,
				}
			],
		}
	)
	co.flags.ignore_permissions = True
	co.insert()
	_notify(_team_and_admins(selection_doc.project), _("أمر تغيير من اختيار: {0}").format(co.title), co.name)
	return co.name


@frappe.whitelist(methods=["POST"])
def engineer_approve(change_order: str) -> str:
	co = frappe.get_doc("Change Order", change_order)
	assert_project_access(co.project)
	if is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	if co.status != "Draft":
		frappe.throw(_("Only a draft can be approved by the engineer"))
	if not co.lines:
		frappe.throw(_("Price the change order first"))
	co.status = "Engineer Approved"
	co.flags.allow_status = True
	co.save(ignore_permissions=True)
	return co.status


@frappe.whitelist(methods=["POST"])
def send_to_client(change_order: str, signer_user: str | None = None) -> dict:
	if not has_full_access():
		frappe.throw(_("Only the office admin sends to the client"), frappe.PermissionError)
	co = frappe.get_doc("Change Order", change_order)
	if co.status != "Engineer Approved":
		frappe.throw(_("The engineer must approve it first"))
	if not signer_user:
		from construction_core.notifications import _clients

		clients = _clients(co.project)
		if not clients:
			frappe.throw(_("Add the client to the project first"))
		signer_user = clients[0]
	from construction_core.esign import create_signature_request, signing_links

	req = create_signature_request("Change Order", co.name, signer_user, _("أمر تغيير: {0}").format(co.title))
	co.signature_request = req.name
	co.status = "Sent to Client"
	co.flags.allow_status = True
	co.save(ignore_permissions=True)
	return signing_links(req)


def on_signed(req) -> str:
	"""Client signed: approve (submit) and apply the effects."""
	co = frappe.get_doc("Change Order", req.reference_name)
	co.status = "Approved"
	co.flags.allow_status = True
	co.flags.ignore_permissions = True
	co.submit()
	apply_effects(co)
	return co.project


def on_declined(req):
	co = frappe.get_doc("Change Order", req.reference_name)
	co.status = "Rejected"
	co.reject_reason = req.decline_reason
	co.flags.allow_status = True
	co.save(ignore_permissions=True)


def apply_effects(co):
	"""Milestone or credit, budget, schedule."""
	amount = D(co.cost_difference)
	if amount > 0:
		m = frappe.get_doc(
			{
				"doctype": "Payment Milestone",
				"project": co.project,
				"project_stage": co.project_stage,
				"label": _("أمر تغيير: {0}").format(co.title),
				"amount": amount,
				"status": "Upcoming" if co.project_stage else "Due",
			}
		)
		m.flags.ignore_permissions = True
		m.insert()
		co.db_set("payment_milestone", m.name)
	elif amount < 0:
		apply_credit(co, co.credit_mode or "Reduce next milestone")
	budget = D(frappe.db.get_value("Project", co.project, "estimated_costing")) + D(co.cost_subtotal)
	frappe.db.set_value("Project", co.project, "estimated_costing", round2(budget))
	if co.schedule_impact_days and int(co.schedule_impact_days) > 0:
		from construction_core.notifications import _clients
		from construction_core.scheduling import shift_stages

		shift_stages(co.project, co.project_stage, co.schedule_impact_days)
		_notify(
			_clients(co.project),
			_("المدة اتمدت {0} يوم بسبب أمر التغيير: {1}").format(co.schedule_impact_days, co.title),
			co.name,
		)


@frappe.whitelist(methods=["POST"])
def apply_credit(co, mode: str = "Reduce next milestone"):
	"""Negative change order: reduce the next unpaid milestone, or a credit note (as the accountant chooses)."""
	if isinstance(co, str):
		if not set(frappe.get_roles()) & {
			"System Manager",
			"Construction Admin",
			"Accounts Manager",
			"Accounts User",
		}:
			frappe.throw(_("Not allowed"), frappe.PermissionError)
		co = frappe.get_doc("Change Order", co)
	credit = -D(co.cost_difference)
	if mode == "Reduce next milestone":
		nxt = frappe.get_all(
			"Payment Milestone",
			filters={"project": co.project, "status": ["in", ["Upcoming", "Due"]], "amount": [">=", credit]},
			fields=["name", "amount"],
			order_by="due_date asc, creation asc",
			limit=1,
		)
		if nxt:
			m = frappe.get_doc("Payment Milestone", nxt[0].name)
			m.amount = round2(D(m.amount) - credit)
			m.add_comment("Comment", _("اتخصم {0} بأمر التغيير {1}").format(credit, co.name))
			m.flags.ignore_permissions = True
			if D(m.amount) == 0:
				m.amount = D("0.01")  # a milestone keeps a positive amount; the accountant can cancel it
			m.save()
			co.db_set("credit_mode", mode)
			return m.name
		mode = "Credit note"
	si = _credit_note(co, credit)
	co.db_set({"credit_mode": "Credit note", "credit_note": si})
	return si


def _credit_note(co, credit) -> str:
	from construction_core.money import ensure_service_item

	project = frappe.get_doc("Project", co.project)
	if not project.customer:
		frappe.throw(_("Set the project's customer first"))
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": project.company,
			"customer": project.customer,
			"project": project.name,
			"posting_date": nowdate(),
			"is_return": 1,
			"disable_rounded_total": 1,
			"items": [
				{
					"item_code": ensure_service_item(),
					"item_name": _("خصم أمر تغيير: {0}").format(co.title),
					"description": _("خصم أمر تغيير: {0}").format(co.title),
					"qty": -1,
					"rate": credit,
				}
			],
		}
	)
	si.flags.ignore_permissions = True
	si.insert()
	return si.name


@frappe.whitelist()
def project_change_orders(project: str) -> list[dict]:
	assert_project_access(project)
	client = is_client()
	rows = frappe.get_list(
		"Change Order",
		filters={"project": project},
		fields=[
			"name",
			"title",
			"status",
			"cost_difference",
			"schedule_impact_days",
			"signature_request",
			"creation",
			"owner",
		],
		order_by="creation desc",
		limit_page_length=0,
	)
	if client:
		# A client sees what was sent to them, plus their own requests while the office prices them
		# (without the draft price).
		user = frappe.session.user
		rows = [r for r in rows if r.status != "Draft" or r.owner == user]
		for r in rows:
			if r.status == "Draft":
				r.cost_difference = None
				r.schedule_impact_days = None
	for r in rows:
		r.pop("owner", None)
	for r in rows:
		r.signed_pdf = (
			frappe.db.get_value("Signature Request", r.signature_request, "signed_pdf")
			if r.signature_request
			else None
		)
	return rows
