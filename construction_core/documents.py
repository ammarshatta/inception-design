"""Project documents with versions, photo/plan markup (phase 14).

- A document keeps every version; the newest is current. Files are private and attached to
  the Project Document.
- Clients see only documents marked client-visible, and only the current version's file:
  the File permission hook below blocks older versions and hidden documents even when the
  client has the URL.
- Downloads go through `download_url`, which records a Frappe Access Log entry.
- A markup never changes the original: the shapes are stored as JSON and the flattened
  drawing is a new private PNG.
"""

import base64
import hashlib
import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from construction_core.permissions import assert_project_access, is_client, is_scoped

FOLDERS = ("عقود", "رسومات", "مواصفات", "تصاريح", "فواتير", "أخرى")
MAX_OVERLAY_SHAPES = 500


def _sha(content: bytes) -> str:
	return hashlib.sha256(content).hexdigest()


def _file_doc(file_url: str):
	name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not name:
		frappe.throw(_("File not found"), frappe.PermissionError)
	return frappe.get_doc("File", name)


def _require_staff():
	if is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)


# --- Library --------------------------------------------------------------------------


@frappe.whitelist()
def project_documents(project: str, search: str | None = None, folder: str | None = None) -> list[dict]:
	"""Documents of one project, newest first. Clients get only visible ones, current version only."""
	assert_project_access(project)
	filters = {"project": project}
	if folder:
		filters["folder"] = folder
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = {"title": ["like", like], "folder": ["like", like]}
	client = is_client()
	if client:
		filters["client_visible"] = 1
	rows = frappe.get_list(
		"Project Document",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "title", "folder", "client_visible", "current_version", "modified"],
		order_by="modified desc",
		limit_page_length=500,
	)
	for r in rows:
		if not client:
			r.versions = frappe.get_all(
				"Document Version",
				filters={"parent": r.name, "parenttype": "Project Document"},
				fields=["version_no", "note", "uploaded_by", "uploaded_on"],
				order_by="version_no desc",
			)
	return rows


def add_version(doc, file_url: str, note: str | None = None, user: str | None = None):
	"""Append a version (the file must already be stored privately)."""
	f = _file_doc(file_url)
	content = f.get_content()
	if isinstance(content, str):
		content = content.encode()
	no = max([cint(v.version_no) for v in doc.versions] or [0]) + 1
	doc.append(
		"versions",
		{
			"version_no": no,
			"file": file_url,
			"note": (note or "")[:140],
			"uploaded_by": user or frappe.session.user,
			"uploaded_on": now_datetime(),
			"sha256": _sha(content),
		},
	)
	return no


@frappe.whitelist(methods=["POST"])
def upload_version(
	project: str,
	file_url: str,
	title: str | None = None,
	folder: str | None = None,
	document: str | None = None,
	note: str | None = None,
	client_visible: int | None = None,
) -> dict:
	"""New document, or a new version of an existing one. The file was uploaded privately by
	this user and is not attached to anything yet."""
	_require_staff()
	assert_project_access(project)
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
		frappe.throw(_("The file was not found"))
	if document:
		doc = frappe.get_doc("Project Document", document)
		if doc.project != project:
			frappe.throw(_("The document belongs to another project"), frappe.PermissionError)
		doc.check_permission("write")
	else:
		if folder not in FOLDERS:
			frappe.throw(_("Choose a folder"))
		if not (title or "").strip():
			frappe.throw(_("Write a title"))
		doc = frappe.get_doc(
			{
				"doctype": "Project Document",
				"project": project,
				"folder": folder,
				"title": title.strip()[:140],
				"client_visible": cint(client_visible),
			}
		)
	add_version(doc, file_url, note)
	if client_visible is not None and document:
		doc.client_visible = cint(client_visible)
	doc.save() if document else doc.insert()
	frappe.db.set_value(
		"File",
		file_name,
		{"attached_to_doctype": "Project Document", "attached_to_name": doc.name, "is_private": 1},
	)
	return {"document": doc.name, "version": doc.current_version}


@frappe.whitelist()
def download_url(document: str, version: int | None = None) -> str:
	"""URL of the current (or, for staff, an older) version; logs the access."""
	doc = frappe.get_doc("Project Document", document)
	doc.check_permission("read")
	assert_project_access(doc.project)
	if version and cint(version) != cint(doc.current_version):
		if is_client():
			frappe.throw(_("Not found"), frappe.PermissionError)
		row = next((v for v in doc.versions if cint(v.version_no) == cint(version)), None)
		if not row:
			frappe.throw(_("Version not found"))
		url = row.file
	else:
		url = doc.current_file
	from frappe.core.doctype.access_log.access_log import make_access_log

	make_access_log(
		doctype="Project Document", document=doc.name, file_type=f"v{version or doc.current_version}"
	)
	return url


def file_has_permission(doc, ptype="read", user=None, debug=False) -> bool:
	"""File hook: for scoped users, a file attached to a Project Document is readable only
	through that document's rules; clients only for a visible document's current version."""
	user = user or frappe.session.user
	if doc.attached_to_doctype != "Project Document" or not doc.attached_to_name:
		return True
	if not is_scoped(user):
		return True
	pd = frappe.db.get_value(
		"Project Document",
		doc.attached_to_name,
		["project", "client_visible", "current_file"],
		as_dict=True,
	)
	if not pd:
		return False
	from construction_core.permissions import is_project_member

	if not is_project_member(pd.project, user):
		return False
	if is_client(user):
		return ptype == "read" and bool(pd.client_visible) and doc.file_url == pd.current_file
	return True


def add_signed_contract(req, project: str | None):
	"""Phase 8 signatures land in the project's "عقود" folder, visible to the client."""
	if not project or not req.signed_pdf:
		return None
	existing = frappe.db.get_value("Project Document", {"signature_request": req.name}, "name")
	if existing:
		return existing
	content = _file_doc(req.signed_pdf).get_content()
	doc = frappe.get_doc(
		{
			"doctype": "Project Document",
			"project": project,
			"folder": "عقود",
			"title": req.title,
			# client contracts are shown to the client; subcontracts are internal
			"client_visible": 0 if req.reference_doctype == "Subcontract" else 1,
			"signature_request": req.name,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{req.name}-signed.pdf",
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Project Document",
			"attached_to_name": doc.name,
		}
	)
	f.flags.ignore_permissions = True
	f.insert()
	add_version(doc, f.file_url, _("نسخة موقّعة"), user="Administrator")
	doc.save(ignore_permissions=True)
	return doc.name


# --- Markup ---------------------------------------------------------------------------

ALLOWED_SHAPES = {"arrow", "circle", "rect", "free", "text"}


def _project_of_file(file_url: str) -> str | None:
	"""The project a file belongs to, through the record it is attached to."""
	f = _file_doc(file_url)
	dt, dn = f.attached_to_doctype, f.attached_to_name
	if not dt or not dn:
		return None
	if dt == "Project":
		return dn
	meta = frappe.get_meta(dt)
	if meta.has_field("project"):
		return frappe.db.get_value(dt, dn, "project")
	return None


def _clean_overlay(overlay) -> str:
	shapes = json.loads(overlay) if isinstance(overlay, str) else overlay
	if not isinstance(shapes, list) or len(shapes) > MAX_OVERLAY_SHAPES:
		frappe.throw(_("Invalid drawing"))
	clean = []
	for s in shapes:
		if not isinstance(s, dict) or s.get("type") not in ALLOWED_SHAPES:
			frappe.throw(_("Invalid drawing"))
		item = {"type": s["type"], "color": str(s.get("color") or "#E5484D")[:16]}
		pts = s.get("points") or []
		if not isinstance(pts, list) or len(pts) > 4000:
			frappe.throw(_("Invalid drawing"))
		item["points"] = [[float(p[0]), float(p[1])] for p in pts]
		if s["type"] == "text":
			item["text"] = str(s.get("text") or "")[:200]
		item["width"] = max(1.0, min(float(s.get("width") or 4), 40.0))
		clean.append(item)
	return json.dumps(clean, ensure_ascii=False)


@frappe.whitelist(methods=["POST"])
def save_markup(
	base_file: str, overlay_json, rendered_png: str, markup: str | None = None, title: str | None = None
) -> dict:
	"""Create or update a markup. The original file is only read, never written."""
	_require_staff()
	project = _project_of_file(base_file)
	if not project:
		frappe.throw(_("This file is not linked to a project"))
	assert_project_access(project)
	base = _file_doc(base_file)
	base_content = base.get_content()
	if isinstance(base_content, str):
		base_content = base_content.encode()
	overlay = _clean_overlay(overlay_json)
	data = rendered_png.split(",", 1)[1] if rendered_png.startswith("data:") else rendered_png
	png = base64.b64decode(data)
	if not png.startswith(b"\x89PNG") or len(png) > 10 * 1024 * 1024:
		frappe.throw(_("Invalid drawing"))
	if markup:
		doc = frappe.get_doc("Markup", markup)
		doc.check_permission("write")
		if doc.base_file != base_file:
			frappe.throw(_("This markup belongs to another file"))
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Markup",
				"project": project,
				"base_file": base_file,
				"base_sha256": _sha(base_content),
				"reference_doctype": base.attached_to_doctype,
				"reference_name": base.attached_to_name,
				"author": frappe.session.user,
			}
		)
	doc.title = (title or doc.title or "")[:140]
	doc.overlay_json = overlay
	doc.save() if markup else doc.insert()
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{doc.name}-{frappe.generate_hash(length=6)}.png",
			"content": png,
			"is_private": 1,
			"attached_to_doctype": "Markup",
			"attached_to_name": doc.name,
			"attached_to_field": "rendered_file",
		}
	)
	f.flags.ignore_permissions = True
	f.insert()
	doc.db_set("rendered_file", f.file_url)
	return {"markup": doc.name, "rendered_file": f.file_url}


@frappe.whitelist()
def get_markup(markup: str) -> dict:
	doc = frappe.get_doc("Markup", markup)
	doc.check_permission("read")
	assert_project_access(doc.project)
	return {
		"name": doc.name,
		"title": doc.title,
		"base_file": doc.base_file,
		"rendered_file": doc.rendered_file,
		"overlay": json.loads(doc.overlay_json or "[]"),
	}


@frappe.whitelist()
def markups_for(base_file: str) -> list[dict]:
	_require_staff()
	project = _project_of_file(base_file)
	if not project:
		return []
	assert_project_access(project)
	return frappe.get_all(
		"Markup",
		filters={"base_file": base_file},
		fields=["name", "title", "rendered_file", "author", "modified"],
		order_by="modified desc",
	)
