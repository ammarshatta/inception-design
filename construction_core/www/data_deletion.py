from frappe import _

from construction_core.branding import get_branding

no_cache = 1


def get_context(context):
	context.title = _("حذف البيانات")
	context.canonical = "/data-deletion"
	context.contact = get_branding()
	return context
