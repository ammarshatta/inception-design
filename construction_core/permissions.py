"""Project-level permissions for construction_core.

Rule (docs/plan/phase-01-data-permissions.md, task 4):
- Users with a full-access role see everything.
- Engineers and clients ("scoped" users) see a project only when they are in its
  `Project User` table, and see project-linked records only for those projects.
- Clients never see a `Stage Update` with `internal_only = 1`.

Other desk users (for example an accountant with ERPNext roles only) keep ERPNext's
normal permissions; these hooks do not restrict them.

These hooks can only deny access. The base read/write rights come from DocPerms
(our DocType JSON, and `setup/install.py` for ERPNext's `Project`).
"""

import frappe
from frappe import _

FULL_ACCESS_ROLES = frozenset({"System Manager", "Construction Admin"})
ENGINEER_ROLE = "Construction Engineer"
CLIENT_ROLE = "Construction Client"
SCOPED_ROLES = frozenset({ENGINEER_ROLE, CLIENT_ROLE})

# DocTypes that carry a `project` Link field and follow the project's access.
PROJECT_LINKED_DOCTYPES = ("Project Stage", "Stage Update", "Payment Milestone", "Project Message")
SCOPED_DOCTYPES = ("Project", *PROJECT_LINKED_DOCTYPES)


def _roles(user: str) -> set[str]:
	return set(frappe.get_roles(user))


def has_full_access(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(_roles(user) & FULL_ACCESS_ROLES)


def is_scoped(user: str | None = None) -> bool:
	"""True when the user is an engineer or client without a full-access role."""
	user = user or frappe.session.user
	if has_full_access(user):
		return False
	return bool(_roles(user) & SCOPED_ROLES)


def is_client(user: str | None = None) -> bool:
	"""A client is a scoped user without the engineer role."""
	user = user or frappe.session.user
	roles = _roles(user)
	return is_scoped(user) and CLIENT_ROLE in roles and ENGINEER_ROLE not in roles


def is_project_member(project: str | None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not project:
		return False
	return bool(frappe.db.exists("Project User", {"parenttype": "Project", "parent": project, "user": user}))


def can_access_project(project: str | None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_scoped(user):
		return True
	return is_project_member(project, user)


def assert_project_access(project: str, ptype: str = "read", user: str | None = None) -> None:
	"""The one helper every API method uses before touching project data.

	Checks project membership and the user's right on the `Project` record
	(`ptype` = "read" for anything that only needs to see the project).
	Never trust a project ID from the browser without calling this first.
	Raises `frappe.PermissionError` on failure.
	"""
	user = user or frappe.session.user
	if not project or not frappe.db.exists("Project", project):
		frappe.throw(_("Project not found"), frappe.PermissionError)
	if not can_access_project(project, user):
		frappe.throw(_("You do not have access to this project"), frappe.PermissionError)
	if not frappe.has_permission("Project", ptype=ptype, doc=project, user=user):
		frappe.throw(_("You do not have access to this project"), frappe.PermissionError)


# --- has_permission hooks -------------------------------------------------------------


def has_permission(doc, ptype: str = "read", user: str | None = None, debug: bool = False) -> bool:
	"""Controller permission for every scoped DocType (registered in hooks.py)."""
	user = user or frappe.session.user
	if not is_scoped(user):
		return True

	if doc.doctype == "Project":
		return is_project_member(doc.name, user)

	if not is_project_member(doc.get("project"), user):
		return False

	if is_client(user):
		if doc.doctype == "Stage Update" and doc.get("internal_only"):
			return False
		if doc.doctype == "Project Message" and ptype == "create" and (doc.get("kind") or "Text") != "Text":
			return False

	return True


# --- permission_query_conditions hooks ------------------------------------------------


def _member_projects_subquery(user: str) -> str:
	return (
		"select `tabProject User`.`parent` from `tabProject User` "
		"where `tabProject User`.`parenttype` = 'Project' "
		f"and `tabProject User`.`user` = {frappe.db.escape(user)}"
	)


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	if not doctype or not is_scoped(user):
		return ""

	members = _member_projects_subquery(user)
	if doctype == "Project":
		return f"`tabProject`.`name` in ({members})"

	condition = f"`tab{doctype}`.`project` in ({members})"
	if doctype == "Stage Update" and is_client(user):
		condition += " and ifnull(`tabStage Update`.`internal_only`, 0) = 0"
	return condition


# --- Signature Request: a client sees only the requests addressed to them ----------------


def signature_request_has_permission(doc, ptype="read", user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if not is_client(user):
		return True
	return ptype == "read" and doc.get("signer_user") == user


def signature_request_query(user=None, doctype=None) -> str:
	user = user or frappe.session.user
	if not is_client(user):
		return ""
	return f"`tabSignature Request`.`signer_user` = {frappe.db.escape(user)}"
