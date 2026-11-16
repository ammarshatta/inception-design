from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint

from construction_core.api.public import list_designs

no_cache = 1
FILTER_KEYS = ("area_min", "area_max", "bedrooms", "bathrooms", "style", "price_max")


def get_context(context):
	args = frappe.form_dict
	filters = {k: args.get(k) for k in FILTER_KEYS if args.get(k)}
	sort = args.get("sort") or "newest"
	page = cint(args.get("page")) or 1
	res = list_designs(filters=filters, sort=sort, page=page)
	context.update(res)
	context.filters = filters
	context.sort = sort
	context.title = _("التصميمات")
	context.description = _("تصميمات شقق بالمساحة وعدد الغرف والستايل والتكلفة التقديرية.")
	context.canonical = "/designs"
	qs = "&".join(f"{k}={quote(str(v))}" for k, v in filters.items())
	context.base_qs = (qs + "&" if qs else "") + f"sort={sort}"
	return context
