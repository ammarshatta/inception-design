"""Portal API (login required). Every method that takes a project calls
`assert_project_access` first (CLAUDE.md rule 5)."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from construction_core.branding import get_branding, get_feature_flags
from construction_core.media import make_public_copy, remove_public_copy, sanitize_photo
from construction_core.permissions import (
	CLIENT_ROLE,
	ENGINEER_ROLE,
	assert_project_access,
	has_full_access,
	is_client,
)

MAX_VIDEO_BYTES = 50 * 1024 * 1024


@frappe.whitelist()
def get_me() -> dict:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	doc = frappe.get_cached_doc("User", user)
	roles = set(frappe.get_roles(user))
	return {
		"user": user,
		"full_name": doc.full_name or doc.first_name or user,
		"roles": {
			"admin": has_full_access(user),
			"engineer": ENGINEER_ROLE in roles,
			"client": CLIENT_ROLE in roles,
		},
		"branding": get_branding(),
		"features": get_feature_flags(),
	}


# --- Engineer portal (phase 3) --------------------------------------------------------


def _current_stage(project: str) -> dict | None:
	stages = frappe.get_all(
		"Project Stage",
		filters={"project": project},
		fields=["name", "stage_name", "status", "progress"],
		order_by="sort_order asc, creation asc",
	)
	for s in stages:
		if s.status == "In Progress":
			return s
	for s in stages:
		if s.status != "Done":
			return s
	return stages[-1] if stages else None


def _last_update_on(project: str):
	rows = frappe.get_list(
		"Stage Update", filters={"project": project}, fields=["creation"], order_by="creation desc", limit=1
	)
	return rows[0].creation if rows else None


@frappe.whitelist()
def my_projects() -> list[dict]:
	"""Projects the user can see (permission_query_conditions do the filtering)."""
	projects = frappe.get_list(
		"Project",
		filters={"status": ["!=", "Cancelled"]},
		fields=["name", "project_name", "weighted_progress", "status"],
		order_by="modified desc",
		limit_page_length=0,
	)
	for p in projects:
		stage = _current_stage(p.name)
		p.current_stage = stage.stage_name if stage else None
		p.last_update_on = _last_update_on(p.name)
	return projects


@frappe.whitelist()
def project_detail(project: str) -> dict:
	assert_project_access(project)
	doc = frappe.get_doc("Project", project)
	stages = frappe.get_list(
		"Project Stage",
		filters={"project": project},
		fields=[
			"name",
			"stage_name",
			"weight",
			"progress",
			"status",
			"progress_mode",
			"planned_start",
			"planned_end",
			"actual_start",
			"actual_end",
		],
		order_by="sort_order asc, creation asc",
		limit_page_length=0,
	)
	return {
		"name": doc.name,
		"project_name": doc.project_name,
		"weighted_progress": flt(doc.get("weighted_progress")),
		"expected_end_date": doc.expected_end_date,
		"area_label": doc.get("area_label"),
		"stages": stages,
		"can_post": not is_client(),
	}


def _stage_project(stage: str) -> str:
	project = frappe.db.get_value("Project Stage", stage, "project")
	if not project:
		frappe.throw(_("Stage not found"), frappe.PermissionError)
	assert_project_access(project)
	return project


def _updates(filters: dict, limit: int = 20) -> list[dict]:
	"""Updates the current user may read (internal ones are filtered out for clients)."""
	updates = frappe.get_list(
		"Stage Update",
		filters=filters,
		fields=[
			"name",
			"project",
			"project_stage",
			"text",
			"progress_after",
			"internal_only",
			"owner",
			"creation",
		],
		order_by="creation desc",
		limit_page_length=limit,
	)
	for u in updates:
		u.author = frappe.utils.get_fullname(u.owner)
		u.media = frappe.get_all(
			"Stage Update Media",
			filters={"parent": u.name, "parenttype": "Stage Update"},
			fields=["name", "file", "kind", "publishable", "taken_at"],
			order_by="idx asc",
		)
	return updates


@frappe.whitelist()
def stage_detail(stage: str) -> dict:
	_stage_project(stage)
	doc = frappe.get_doc("Project Stage", stage)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name"),
		"stage_name": doc.stage_name,
		"status": doc.status,
		"progress": flt(doc.progress),
		"progress_mode": doc.progress_mode,
		"checklist": [
			{"name": r.name, "label": r.label, "done": cint(r.done), "done_on": r.done_on}
			for r in doc.checklist
		],
		"updates": _updates({"project_stage": stage}),
		"can_post": not is_client(),
	}


@frappe.whitelist(methods=["POST"])
def toggle_checklist_item(stage: str, row_name: str, done: int) -> dict:
	_stage_project(stage)
	doc = frappe.get_doc("Project Stage", stage)
	doc.check_permission("write")
	row = next((r for r in doc.checklist if r.name == row_name), None)
	if not row:
		frappe.throw(_("Checklist item not found"))
	row.done = cint(done)
	doc.save()
	return {
		"progress": flt(doc.progress),
		"project_progress": flt(frappe.db.get_value("Project", doc.project, "weighted_progress")),
	}


@frappe.whitelist(methods=["POST"])
def create_stage_update(
	project: str,
	stage: str,
	text: str | None = None,
	progress_after: float | None = None,
	internal_only: int = 0,
) -> str:
	assert_project_access(project)
	if is_client():
		frappe.throw(_("Clients cannot post updates"), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": "Stage Update",
			"project": project,
			"project_stage": stage,
			"text": text,
			"progress_after": flt(progress_after) if progress_after not in (None, "") else 0,
			"internal_only": cint(internal_only),
		}
	)
	doc.insert()
	return doc.name


def _get_update_for_write(update: str):
	doc = frappe.get_doc("Stage Update", update)
	assert_project_access(doc.project)
	doc.check_permission("write")
	return doc


@frappe.whitelist(methods=["POST"])
def attach_media(update: str, file_url: str, kind: str = "Photo") -> dict:
	"""Link an uploaded private file to the update. Photos are re-checked on the server:
	at most 1600 px and stripped of EXIF/GPS, even if the browser did not resize them."""
	if kind not in ("Photo", "Video"):
		frappe.throw(_("Unknown media type"))
	doc = _get_update_for_write(update)
	file = frappe.db.get_value(
		"File",
		{"file_url": file_url, "attached_to_doctype": "Stage Update", "attached_to_name": update},
		["name", "file_size", "is_private"],
		as_dict=True,
	)
	if not file:
		frappe.throw(_("The file was not uploaded to this update"))
	if kind == "Video" and cint(file.file_size) > MAX_VIDEO_BYTES:
		frappe.throw(_("الفيديو أكبر من 50 ميجا"))
	if kind == "Photo":
		sanitize_photo(file.name)
	row = doc.append("media", {"file": file_url, "kind": kind, "taken_at": frappe.utils.now_datetime()})
	doc.save()
	return {"row": row.name, "file": file_url}


@frappe.whitelist(methods=["POST"])
def set_media_publishable(update: str, row_name: str, value: int) -> dict:
	doc = _get_update_for_write(update)
	row = next((r for r in doc.media if r.name == row_name), None)
	if not row:
		frappe.throw(_("Photo not found"))
	if row.kind != "Photo":
		frappe.throw(_("Only photos can be published"))
	row.publishable = cint(value)
	if row.publishable and not row.public_file:
		row.public_file = make_public_copy(row.file, update)
	elif not row.publishable and row.public_file:
		remove_public_copy(row.public_file)
		row.public_file = None
	doc.save()
	return {"publishable": row.publishable}


# --- Client portal (phase 4) ----------------------------------------------------------


def _next_payment(project: str) -> dict | None:
	rows = frappe.get_list(
		"Payment Milestone",
		filters={"project": project, "status": ["in", ["Due", "Invoiced", "Upcoming"]]},
		fields=["name", "label", "amount", "status", "due_date", "creation"],
		order_by="creation asc",
		limit_page_length=0,
	)
	rank = {"Due": 0, "Invoiced": 1, "Upcoming": 2}
	rows.sort(key=lambda r: (rank[r.status], str(r.due_date or "9999"), str(r.creation)))
	return rows[0] if rows else None


@frappe.whitelist()
def client_home(project: str) -> dict:
	assert_project_access(project)
	doc = frappe.get_doc("Project", project)
	stage = _current_stage(project)
	return {
		"name": doc.name,
		"project_name": doc.project_name,
		"weighted_progress": flt(doc.get("weighted_progress")),
		"expected_end_date": doc.expected_end_date,
		"current_stage": stage.stage_name if stage else None,
		"updates": _updates({"project": project}, limit=3),
		"next_payment": _next_payment(project),
		"pending_approvals": frappe.get_list(
			"Project Message",
			filters={"project": project, "kind": "Approval", "approval_status": "Pending"},
			fields=["name", "approval_title", "approval_amount"],
			order_by="creation asc",
		),
	}


def delay_days(stage: dict, today=None) -> int:
	"""Days past the planned end: finished late, or still open after the planned end."""
	from frappe.utils import date_diff, getdate, nowdate

	if not stage.get("planned_end"):
		return 0
	end = stage.get("actual_end")
	if not end:
		if stage.get("status") == "Done":
			return 0
		end = today or nowdate()
	return max(0, date_diff(getdate(end), getdate(stage["planned_end"])))


@frappe.whitelist()
def timeline(project: str) -> dict:
	assert_project_access(project)
	stages = project_detail(project)["stages"]
	for s in stages:
		s["delay_days"] = delay_days(s)
	return {"project": project, "stages": stages}


@frappe.whitelist()
def gallery(project: str, stage: str | None = None) -> dict:
	assert_project_access(project)
	filters = {"project": project}
	if stage:
		filters["project_stage"] = stage
	updates = _updates(filters, limit=200)
	stage_names = dict(
		frappe.get_all(
			"Project Stage", filters={"project": project}, fields=["name", "stage_name"], as_list=True
		)
	)
	groups = []
	for u in updates:
		photos = [m for m in u.media]
		if photos:
			groups.append(
				{
					"update": u.name,
					"stage": u.project_stage,
					"stage_name": stage_names.get(u.project_stage),
					"date": u.creation,
					"text": u.text,
					"author": u.author,
					"media": photos,
				}
			)
	return {"groups": groups, "stages": [{"name": k, "stage_name": v} for k, v in stage_names.items()]}


@frappe.whitelist()
def payments(project: str) -> dict:
	assert_project_access(project)
	rows = frappe.get_list(
		"Payment Milestone",
		filters={"project": project},
		fields=["name", "label", "amount", "status", "due_date", "sales_invoice"],
		order_by="due_date asc, creation asc",
		limit_page_length=0,
	)
	paid = sum(flt(r.amount) for r in rows if r.status == "Paid")
	total = sum(flt(r.amount) for r in rows)
	for r in rows:
		r.has_invoice = bool(
			r.sales_invoice and frappe.db.get_value("Sales Invoice", r.sales_invoice, "docstatus") == 1
		)
	return {
		"milestones": rows,
		"total": flt(total, 2),
		"paid": flt(paid, 2),
		"remaining": flt(total - paid, 2),
		"currency": frappe.db.get_value(
			"Company", frappe.db.get_value("Project", project, "company"), "default_currency"
		),
	}


@frappe.whitelist()
def invoice_pdf(milestone: str):
	"""Arabic RTL PDF of the submitted invoice linked to a milestone of the user's project."""
	from werkzeug.wrappers import Response

	project, invoice = frappe.db.get_value("Payment Milestone", milestone, ["project", "sales_invoice"]) or (
		None,
		None,
	)
	assert_project_access(project)
	frappe.get_doc("Payment Milestone", milestone).check_permission("read")
	if not invoice or frappe.db.get_value("Sales Invoice", invoice, "docstatus") != 1:
		frappe.throw(_("No invoice yet"), frappe.DoesNotExistError)
	pdf = frappe.get_print(
		"Sales Invoice", invoice, print_format=INVOICE_PRINT_FORMAT, as_pdf=True, no_letterhead=1
	)
	resp = Response(pdf, content_type="application/pdf")
	resp.headers["Content-Disposition"] = f'attachment; filename="{invoice}.pdf"'
	return resp


INVOICE_PRINT_FORMAT = "Inceptiondesign Invoice"


def _message_row(m) -> dict:
	return {
		"name": m.name,
		"kind": m.kind,
		"text": m.text,
		"attachment": m.attachment,
		"approval_title": m.approval_title,
		"approval_detail": m.approval_detail,
		"approval_amount": m.approval_amount,
		"approval_status": m.approval_status,
		"answer_note": m.answer_note,
		"answered_on": m.answered_on,
		"owner": m.owner,
		"author": frappe.utils.get_fullname(m.owner),
		"mine": m.owner == frappe.session.user,
		"creation": m.creation,
	}


MESSAGE_FIELDS = [
	"name",
	"kind",
	"text",
	"attachment",
	"approval_title",
	"approval_detail",
	"approval_amount",
	"approval_status",
	"answer_note",
	"answered_on",
	"owner",
	"creation",
]


@frappe.whitelist()
def messages(
	project: str, before: str | None = None, after: str | None = None, limit: int = 30
) -> list[dict]:
	assert_project_access(project)
	filters = [["project", "=", project]]
	if before:
		filters.append(["creation", "<", before])
	if after:
		filters.append(["creation", ">", after])
	rows = frappe.get_list(
		"Project Message",
		filters=filters,
		fields=MESSAGE_FIELDS,
		order_by="creation desc",
		limit_page_length=min(cint(limit) or 30, 100),
	)
	return [_message_row(m) for m in reversed(rows)]


@frappe.whitelist(methods=["POST"])
def send_message(project: str, text: str | None = None, file_url: str | None = None) -> dict:
	assert_project_access(project)
	text = (text or "").strip()
	if not text and not file_url:
		frappe.throw(_("Write a message or attach a photo"))
	file_name = None
	if file_url:
		# The photo was uploaded privately by this user and is not attached to anything yet.
		file_name = frappe.db.get_value(
			"File",
			{
				"file_url": file_url,
				"owner": frappe.session.user,
				"is_private": 1,
				"attached_to_name": ["is", "not set"],
			},
			"name",
		)
		if not file_name:
			frappe.throw(_("The photo was not found"))
	doc = frappe.get_doc(
		{
			"doctype": "Project Message",
			"project": project,
			"kind": "Text",
			"text": text,
			"attachment": file_url,
		}
	)
	doc.insert()
	if file_name:
		frappe.db.set_value(
			"File",
			file_name,
			{
				"attached_to_doctype": "Project Message",
				"attached_to_name": doc.name,
				"attached_to_field": "attachment",
			},
		)
	return _message_row(doc)


@frappe.whitelist(methods=["POST"])
def request_approval(
	project: str, title: str, detail: str | None = None, amount: float | None = None
) -> dict:
	assert_project_access(project)
	if is_client():
		frappe.throw(_("Only the engineer or the office can request an approval"), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": "Project Message",
			"project": project,
			"kind": "Approval",
			"approval_title": title,
			"approval_detail": detail,
			"approval_amount": flt(amount) if amount not in (None, "") else 0,
			"approval_status": "Pending",
		}
	)
	doc.insert()
	return _message_row(doc)


@frappe.whitelist(methods=["POST"])
def answer_approval(message: str, answer: str, note: str | None = None) -> dict:
	if answer not in ("Approved", "Question"):
		frappe.throw(_("The answer must be Approved or Question"))
	project = frappe.db.get_value("Project Message", message, "project")
	assert_project_access(project)
	doc = frappe.get_doc("Project Message", message)
	if doc.kind != "Approval":
		frappe.throw(_("This message is not an approval request"))
	if not is_client():
		frappe.throw(_("Only the client answers approvals"), frappe.PermissionError)
	doc.approval_status = answer
	doc.answer_note = note
	doc.save()
	return _message_row(doc)
