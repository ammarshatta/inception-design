"""/p/<project>?t=<token>: the project page for visitors.

The real page is built in phase 5. Until then a valid link shows a placeholder,
and an invalid, revoked or expired link returns 404 (story P02-06).
No project data is shown here (CLAUDE.md rule 6: public output is an allowlist).
"""

import frappe
from frappe import _

from construction_core.branding import get_branding
from construction_core.sharing import check_share_token

no_cache = 1


def get_context(context):
	project = frappe.form_dict.get("project")
	token = frappe.form_dict.get("t")
	if not check_share_token(project, token):
		raise frappe.PageDoesNotExistError
	context.no_cache = 1
	context.branding = get_branding()
	context.title = _("Project page")
	return context
