from frappe import _

from construction_core.api.public import list_public_projects

no_cache = 1


def get_context(context):
	context.projects = list_public_projects()
	context.title = _("مشاريعنا")
	context.description = _("مشاريع تشطيب شغالين فيها، بنسبة الإنجاز وصور الموقع.")
	context.canonical = "/projects"
	return context
