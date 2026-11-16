"""Finish selections (phase 9)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate

from construction_core.costing import engine
from construction_core.costing.engine import D, round2
from construction_core.permissions import assert_project_access, has_full_access, is_client


def option_price(option: str, on_date=None) -> D:
	"""Price of one unit of an option: from the price library when it has an item."""
	opt = frappe.get_cached_doc("Selection Option", option)
	if opt.item:
		try:
			return engine.material_price(opt.item, on_date or nowdate())
		except frappe.ValidationError:
			frappe.clear_last_message()
	return D(opt.unit_price)


def price_difference(unit_price, qty, allowance_amount) -> D:
	"""(option price − allowance ÷ qty) × qty, i.e. the option's total minus the allowance."""
	qty = D(qty)
	if not qty:
		return D(0)
	return round2((D(unit_price) - D(allowance_amount) / qty) * qty)


def _selection_for_client(selection: str):
	doc = frappe.get_doc("Project Selection", selection)
	assert_project_access(doc.project)
	if not is_client():
		frappe.throw(_("Only the client chooses"), frappe.PermissionError)
	return doc


@frappe.whitelist()
def project_selections(project: str) -> list[dict]:
	"""Selections of a project with their options and the live price effect of each option."""
	assert_project_access(project)
	rows = frappe.get_list(
		"Project Selection",
		filters={"project": project, "status": ["!=", "Superseded"]},
		fields=[
			"name",
			"title",
			"category",
			"room_or_area",
			"qty",
			"uom",
			"allowance_amount",
			"due_date",
			"status",
			"chosen_option",
			"chosen_unit_price",
			"price_difference",
			"signature_request",
		],
		order_by="due_date asc, creation asc",
		limit_page_length=0,
	)
	for r in rows:
		opts = frappe.get_all(
			"Selection Option",
			filters={"category": r.category, "active": 1},
			fields=["name", "option_name", "brand", "origin"],
			order_by="option_name asc",
		)
		for o in opts:
			price = option_price(o.name)
			o.unit_price = price
			o.difference = price_difference(price, r.qty, r.allowance_amount)
			o.images = frappe.get_all(
				"Selection Option Image",
				filters={"parent": o.name, "parenttype": "Selection Option"},
				pluck="file",
				order_by="idx asc",
			)
		r.options = opts
		r.allowance_per_unit = round2(D(r.allowance_amount) / D(r.qty)) if r.qty else D(0)
	return rows


@frappe.whitelist(methods=["POST"])
def choose(selection: str, option: str) -> dict:
	doc = _selection_for_client(selection)
	if doc.status not in ("Open", "Chosen"):
		frappe.throw(_("This selection is locked"), frappe.PermissionError)
	opt = frappe.get_doc("Selection Option", option)
	if opt.category != doc.category or not opt.active:
		frappe.throw(_("This option is not available for this selection"))
	price = option_price(option)
	doc.chosen_option = option
	doc.chosen_unit_price = price
	doc.price_difference = price_difference(price, doc.qty, doc.allowance_amount)
	doc.status = "Chosen"
	doc.flags.allow_system_update = True
	doc.save(ignore_permissions=True)
	return {"status": doc.status, "price_difference": doc.price_difference}


@frappe.whitelist(methods=["POST"])
def approve(selection: str) -> dict:
	"""Within the allowance: approved and locked. Over it: the client signs first."""
	doc = _selection_for_client(selection)
	if doc.status != "Chosen":
		frappe.throw(_("Choose an option first"))
	if D(doc.price_difference) > 0:
		from construction_core.esign import create_signature_request

		req = create_signature_request(
			"Project Selection",
			doc.name,
			frappe.session.user,
			_("اختيار {0}: فرق {1}").format(doc.title, doc.price_difference),
		)
		doc.signature_request = req.name
		doc.status = "Awaiting Signature"
		doc.flags.allow_system_update = True
		doc.save(ignore_permissions=True)
		return {"status": doc.status, "signature_request": req.name}
	_lock(doc)
	return {"status": doc.status}


def _lock(doc):
	doc.status = "Locked"
	doc.approved_on = now_datetime()
	doc.flags.allow_system_update = True
	doc.save(ignore_permissions=True)
	if D(doc.price_difference) > 0:
		from construction_core.change_orders import draft_from_selection

		co = draft_from_selection(doc)
		doc.db_set("change_order", co)


def on_signed(req) -> str:
	doc = frappe.get_doc("Project Selection", req.reference_name)
	_lock(doc)
	return doc.project


def on_declined(req):
	doc = frappe.get_doc("Project Selection", req.reference_name)
	doc.status = "Chosen"
	doc.flags.allow_system_update = True
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def unlock(selection: str, reason: str) -> str:
	"""Admin override, logged. A signed selection gets a new revision instead of being edited."""
	if not has_full_access():
		frappe.throw(_("Only the office admin can unlock"), frappe.PermissionError)
	if not (reason or "").strip():
		frappe.throw(_("Write the reason"))
	doc = frappe.get_doc("Project Selection", selection)
	doc.add_comment("Comment", _("اتفتح تاني: {0}").format(reason.strip()))
	signed = (
		doc.signature_request
		and frappe.db.get_value("Signature Request", doc.signature_request, "status") == "Signed"
	)
	if signed:
		new = frappe.copy_doc(doc)
		for f in (
			"chosen_option",
			"chosen_unit_price",
			"price_difference",
			"signature_request",
			"change_order",
			"approved_on",
		):
			new.set(f, None)
		new.status = "Open"
		new.previous_selection = doc.name
		new.flags.allow_system_update = True
		new.insert(ignore_permissions=True)
		doc.status = "Superseded"
		doc.flags.allow_system_update = True
		doc.save(ignore_permissions=True)
		return new.name
	doc.status = "Open"
	doc.flags.allow_system_update = True
	doc.save(ignore_permissions=True)
	return doc.name


def send_reminders():
	"""Daily: remind the client 3 days before a due date and on the day."""
	from construction_core.notifications import _clients, _notify

	for days, text in ((3, _("فاضل 3 أيام على اختيار: {0}")), (0, _("النهارده آخر ميعاد لاختيار: {0}"))):
		for s in frappe.get_all(
			"Project Selection",
			filters={"status": ["in", ["Open", "Chosen"]], "due_date": add_days(nowdate(), days)},
			fields=["name", "project", "title"],
		):
			_notify(_clients(s.project), text.format(s.title), "Project Selection", s.name)


def overdue_for_project(project: str) -> list[dict]:
	return frappe.get_all(
		"Project Selection",
		filters={"project": project, "status": ["in", ["Open", "Chosen"]], "due_date": ["<", nowdate()]},
		fields=["name", "title", "due_date"],
	)
