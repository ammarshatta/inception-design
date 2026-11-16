"""Demo content for the public site (phase 5, task 5).

    bench --site <site> execute construction_core.setup.demo.install
    bench --site <site> execute construction_core.setup.demo.remove   # before launch

Images are drawn here (no stock photos), so nothing needs a licence.
"""

import io

import frappe
from PIL import Image, ImageDraw

DEMO_SLUG = "demo-modern-160"
DEMO_TEMPLATE = "قالب تجريبي: شقة مودرن"
DEMO_MARK = "[DEMO]"
STAGES = [
	("تأسيس سباكة وكهرباء", 22),
	("محارة", 15),
	("أرضيات وسيراميك", 20),
	("نجارة وألوميتال", 15),
	("دهانات", 18),
	("تشطيب نهائي وتسليم", 10),
]


def _room(color, accent, w=1200, h=900) -> bytes:
	img = Image.new("RGB", (w, h), color)
	d = ImageDraw.Draw(img)
	d.rectangle([0, int(h * 0.7), w, h], fill=accent)
	d.rectangle(
		[int(w * 0.62), int(h * 0.12), int(w * 0.9), int(h * 0.55)],
		fill=(234, 241, 244),
		outline=(255, 255, 255),
		width=12,
	)
	d.rounded_rectangle(
		[int(w * 0.1), int(h * 0.5), int(w * 0.55), int(h * 0.7)], radius=24, fill=(111, 127, 120)
	)
	out = io.BytesIO()
	img.save(out, format="JPEG", quality=82)
	return out.getvalue()


def _floor_plan(w=1200, h=900) -> bytes:
	img = Image.new("RGB", (w, h), (255, 255, 255))
	d = ImageDraw.Draw(img)
	d.rectangle([60, 60, w - 60, h - 60], outline=(23, 32, 29), width=10)
	d.line([w // 2, 60, w // 2, h - 60], fill=(23, 32, 29), width=6)
	d.line([60, h // 2, w // 2, h // 2], fill=(23, 32, 29), width=6)
	d.line([w // 2, int(h * 0.65), w - 60, int(h * 0.65)], fill=(23, 32, 29), width=6)
	out = io.BytesIO()
	img.save(out, format="PNG")
	return out.getvalue()


def _attach(name, content, docname):
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": name,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Design Template",
			"attached_to_name": docname,
		}
	).insert(ignore_permissions=True)
	return f.file_url


def install():
	if frappe.db.exists("Design Template", DEMO_SLUG):
		return DEMO_SLUG
	if not frappe.db.exists("Phase Template", DEMO_TEMPLATE):
		frappe.get_doc(
			{
				"doctype": "Phase Template",
				"template_name": DEMO_TEMPLATE,
				"description": DEMO_MARK,
				"stages": [{"stage_name": n, "weight": w} for n, w in STAGES],
			}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "Design Template",
			"title": "مودرن هادي (تجريبي)",
			"slug": DEMO_SLUG,
			"published": 0,
			"style": "مودرن",
			"area_m2": 160,
			"bedrooms": 3,
			"bathrooms": 2,
			"cost_from": 450000,
			"cost_to": 520000,
			"duration_weeks": 16,
			"phase_template": DEMO_TEMPLATE,
			"description": f"<p>{DEMO_MARK} تصميم تجريبي لعرض شكل الصفحة. احذفه قبل الإطلاق.</p>",
		}
	).insert(ignore_permissions=True)
	doc.cover = _attach("demo-cover.jpg", _room((232, 225, 214), (184, 156, 122)), doc.name)
	for i, (color, accent) in enumerate(
		[
			((239, 232, 221), (201, 184, 160)),
			((246, 245, 242), (216, 212, 204)),
			((230, 236, 232), (150, 140, 120)),
		]
	):
		doc.append(
			"media",
			{
				"file": _attach(f"demo-render-{i + 1}.jpg", _room(color, accent), doc.name),
				"kind": "3D",
				"caption": f"رندر {i + 1}",
			},
		)
	doc.append(
		"media",
		{
			"file": _attach("demo-floor-plan.png", _floor_plan(), doc.name),
			"kind": "Floor Plan",
			"caption": "المسقط الأفقي",
		},
	)
	doc.published = 1
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def remove():
	"""Deletes the demo design, its files (private and public copies) and the demo template."""
	if frappe.db.exists("Design Template", DEMO_SLUG):
		for f in frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Design Template", "attached_to_name": DEMO_SLUG},
			pluck="name",
		):
			frappe.delete_doc("File", f, ignore_permissions=True, force=True)
		frappe.delete_doc("Design Template", DEMO_SLUG, ignore_permissions=True, force=True)
	if frappe.db.exists("Phase Template", DEMO_TEMPLATE):
		frappe.delete_doc("Phase Template", DEMO_TEMPLATE, ignore_permissions=True, force=True)
	frappe.db.commit()
	return "removed"
