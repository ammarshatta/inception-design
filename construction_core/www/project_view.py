"""/projects/<slug> (public projects) — same page body as /p/<project>?t=<token>."""

import frappe

from construction_core.api.public import NotFound, get_public_project

no_cache = 1


def get_context(context):
	try:
		context.p = get_public_project(slug=frappe.form_dict.get("slug"))
	except NotFound:
		raise frappe.PageDoesNotExistError
	context.title = context.p["title"]
	context.canonical = f"/projects/{frappe.form_dict.get('slug')}"
	if context.p.get("photos"):
		context.og_image = context.p["photos"][0]["url"]
	return context
