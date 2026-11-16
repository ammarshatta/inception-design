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
