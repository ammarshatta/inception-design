import frappe
from frappe import _

from construction_core.api.public import NotFound, get_public_design

no_cache = 1

GOVERNORATES = [
	"القاهرة", "الجيزة", "الإسكندرية", "القليوبية", "الشرقية", "الدقهلية", "الغربية", "المنوفية",
	"البحيرة", "كفر الشيخ", "دمياط", "بورسعيد", "الإسماعيلية", "السويس", "الفيوم", "بني سويف",
	"المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان", "البحر الأحمر", "مطروح",
	"شمال سيناء", "جنوب سيناء", "الوادي الجديد",
]  # fmt: skip


def get_context(context):
	try:
		d = get_public_design(frappe.form_dict.get("slug"))
	except NotFound:
		raise frappe.PageDoesNotExistError
	context.d = d
	context.floor_plans = [m for m in d["media"] if m["kind"] == "Floor Plan"]
	context.gallery = [m for m in d["media"] if m["kind"] != "Floor Plan"]
	context.governorates = GOVERNORATES
	context.title = d["title"]
	context.description = _("تصميم {0}: {1} م²، التكلفة التقديرية والمراحل.").format(
		d["title"], int(d["area_m2"])
	)
	context.og_image = d["cover"]
	context.canonical = f"/designs/{d['slug']}"
	return context
