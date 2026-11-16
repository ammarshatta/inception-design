"""/p/<project>?t=<token>: a project shared by secret link (noindex).

Invalid, revoked or expired links return the same 404 as a missing project.
"""

import frappe

from construction_core.api.public import NotFound, get_public_project

no_cache = 1


def get_context(context):
	try:
		context.p = get_public_project(slug=frappe.form_dict.get("project"), token=frappe.form_dict.get("t"))
	except NotFound:
		raise frappe.PageDoesNotExistError
	context.title = context.p["title"]
	context.noindex = 1
	return context
