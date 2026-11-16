import frappe
from frappe import _

from construction_core.api.public import list_designs, list_public_projects
from construction_core.branding import get_branding

no_cache = 1


def get_context(context):
	b = get_branding()
	context.title = b["office_name"] or _("التشطيب")
	context.description = _("تصميمات شقق جاهزة للتنفيذ، ومتابعة كل مرحلة بالصور.")
	context.canonical = "/"
	context.designs = list_designs(sort="newest")["designs"][:6]
	context.projects = list_public_projects()[:3]
	return context
