"""Phase 14: document versions and client visibility, markup, takeoff geometry and push to estimate."""

import base64
import hashlib
import io
import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate
from PIL import Image

from construction_core import documents, takeoff
from construction_core.tests.factories import make_update, make_world, stages_of
from construction_core.tests.test_money import make_customer

SALES = "cc-sales-docs@example.com"


def private_file(user: str, name: str, content: bytes, attached_to: tuple | None = None) -> str:
	with_user = frappe.session.user
	frappe.set_user(user)
	try:
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": name,
				"content": content,
				"is_private": 1,
				**(
					{"attached_to_doctype": attached_to[0], "attached_to_name": attached_to[1]}
					if attached_to
					else {}
				),
			}
		)
		f.insert(ignore_permissions=bool(attached_to))
		return f.file_url
	finally:
		frappe.set_user(with_user)


def png(color=(200, 0, 0)) -> bytes:
	out = io.BytesIO()
	Image.new("RGB", (40, 30), color).save(out, format="PNG")
	return out.getvalue()


def can_read_file(user: str, file_url: str) -> bool:
	f = frappe.get_doc("File", {"file_url": file_url})
	return bool(frappe.has_permission("File", "read", doc=f, user=user))


class TestGeometry(IntegrationTestCase):
	def test_rectangle_4_by_5_is_20(self):
		scale = takeoff.scale_px_per_m([(0, 0), (250, 0)], 5)  # 250 px = 5 m → 50 px/m
		self.assertEqual(scale, 50)
		rect = [(100, 100), (300, 100), (300, 350), (100, 350)]  # 200 × 250 px
		self.assertAlmostEqual(takeoff.measure("Area", rect, scale), 20.0)
		self.assertAlmostEqual(takeoff.measure("Length", [*rect, rect[0]], scale), 18.0)  # perimeter

	def test_l_shape_and_count(self):
		scale = 100  # px per m
		# 6×4 m minus a 3×2 m corner = 18 m²; counter-clockwise order gives the same area
		l_shape = [(0, 0), (600, 0), (600, 200), (300, 200), (300, 400), (0, 400)]
		self.assertAlmostEqual(takeoff.measure("Area", l_shape, scale), 18.0)
		self.assertAlmostEqual(takeoff.measure("Area", list(reversed(l_shape)), scale), 18.0)
		self.assertEqual(takeoff.measure("Count", [(1, 1), (2, 2), (3, 3)], scale), 3)
		self.assertRaises(frappe.ValidationError, takeoff.scale_px_per_m, [(0, 0), (0, 0)], 5)


class TestDocuments(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def upload(self, content: bytes, name: str, **kw):
		url = private_file(self.w.users.eng1, name, content)
		with self.set_user(self.w.users.eng1):
			return documents.upload_version(self.w.p1, url, **kw), url

	def test_versions_and_client_visibility(self):
		(res1, v1) = self.upload(
			b"%PDF-1.4 plan v1", "plan-v1.pdf", title="مسقط أفقي", folder="رسومات", client_visible=1
		)
		(res2, v2) = self.upload(
			b"%PDF-1.4 plan v2", "plan-v2.pdf", document=res1["document"], note="تعديل المطبخ"
		)
		self.assertEqual((res1["version"], res2["version"]), (1, 2))
		doc = frappe.get_doc("Project Document", res1["document"])
		self.assertEqual((doc.current_version, doc.current_file), (2, v2))
		(hidden, h1) = self.upload(
			b"%PDF-1.4 internal", "boq.pdf", title="مقايسة داخلية", folder="مواصفات", client_visible=0
		)

		# staff: both versions stay downloadable
		self.assertTrue(can_read_file(self.w.users.eng1, v1))
		self.assertTrue(can_read_file(self.w.users.eng1, v2))
		with self.set_user(self.w.users.eng1):
			self.assertEqual(documents.download_url(doc.name, 1), v1)
		# client: only visible documents, current version only, even with the URL
		c = self.w.users.client1
		with self.set_user(c):
			rows = documents.project_documents(self.w.p1)
			self.assertEqual([r.name for r in rows if r.name in (doc.name, hidden["document"])], [doc.name])
			self.assertNotIn("versions", rows[0])
			self.assertEqual(documents.download_url(doc.name), v2)
			self.assertRaises(frappe.PermissionError, documents.download_url, doc.name, 1)
			self.assertRaises(frappe.PermissionError, documents.download_url, hidden["document"])
		self.assertTrue(can_read_file(c, v2))
		self.assertFalse(can_read_file(c, v1))
		self.assertFalse(can_read_file(c, h1))
		self.assertFalse(can_read_file(self.w.users.client2, v2), "other project's client")
		self.assertFalse(can_read_file(self.w.users.eng2, v2), "other project's engineer")
		# old versions cannot be edited
		doc.versions[0].file = v2
		self.assertRaises(frappe.ValidationError, doc.save, ignore_permissions=True)
		# search by title or folder
		with self.set_user(self.w.users.eng1):
			self.assertIn(doc.name, [r.name for r in documents.project_documents(self.w.p1, search="مسقط")])
			self.assertIn(doc.name, [r.name for r in documents.project_documents(self.w.p1, search="رسومات")])
			self.assertNotIn(
				doc.name, [r.name for r in documents.project_documents(self.w.p1, search="تصاريح")]
			)
		self.assertTrue(frappe.db.exists("Access Log", {"reference_document": doc.name}))

	def test_markup_keeps_original(self):
		update = make_update(self.w.p1, stages_of(self.w.p1)[0])
		original = png()
		base = private_file("Administrator", "site.png", original, ("Stage Update", update))
		before = hashlib.sha256(
			open(frappe.get_doc("File", {"file_url": base}).get_full_path(), "rb").read()
		).hexdigest()
		shapes = [
			{"type": "arrow", "color": "#E5484D", "points": [[1, 1], [20, 20]]},
			{"type": "text", "color": "#E5484D", "points": [[5, 5]], "text": "الشرخ هنا"},
		]
		rendered = "data:image/png;base64," + base64.b64encode(png((0, 0, 200))).decode()
		with self.set_user(self.w.users.eng1):
			res = documents.save_markup(base, json.dumps(shapes), rendered, title="شرخ")
			again = documents.get_markup(res["markup"])
			self.assertEqual([s["type"] for s in again["overlay"]], ["arrow", "text"])
			self.assertEqual(again["overlay"][1]["text"], "الشرخ هنا")
			shapes.append({"type": "circle", "color": "#1D6B57", "points": [[10, 10], [15, 15]]})
			res2 = documents.save_markup(base, shapes, rendered, markup=res["markup"])
			self.assertEqual(res2["markup"], res["markup"])
			self.assertEqual(len(documents.get_markup(res["markup"])["overlay"]), 3)
		after = hashlib.sha256(
			open(frappe.get_doc("File", {"file_url": base}).get_full_path(), "rb").read()
		).hexdigest()
		self.assertEqual(before, after, "original unchanged")
		self.assertEqual(frappe.db.get_value("Markup", res["markup"], "base_sha256"), before)
		self.assertTrue(frappe.get_doc("File", {"file_url": res2["rendered_file"]}).is_private)
		with self.set_user(self.w.users.client1):
			self.assertRaises(frappe.PermissionError, documents.get_markup, res["markup"])
		with self.set_user(self.w.users.eng2):
			self.assertRaises(frappe.PermissionError, documents.save_markup, base, shapes, rendered)


class TestTakeoffToEstimate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", SALES):
			u = frappe.get_doc(
				{"doctype": "User", "email": SALES, "first_name": "مبيعات", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
			u.add_roles("Construction Sales")

	def test_measure_and_push(self):
		est = frappe.get_doc(
			{
				"doctype": "Estimate",
				"title": "تسعير من الرسم",
				"customer": make_customer("عميل الرسم"),
				"estimate_date": nowdate(),
				"lines": [
					{
						"section": "أرضيات",
						"line_type": "Other",
						"description": "سيراميك",
						"qty": 1,
						"unit_cost": 300,
					}
				],
			}
		).insert(ignore_permissions=True)
		with self.set_user(SALES):
			tk = takeoff.save_takeoff(
				{
					"title": "مسقط الشقة",
					"estimate": est.name,
					"drawing_file": "/private/files/plan.pdf",
					"calibration": [[0, 0], [250, 0]],
					"calibration_m": 5,
					"measurements": [
						{
							"label": "الريسبشن",
							"kind": "Area",
							"points": [[0, 0], [200, 0], [200, 250], [0, 250]],
						},
						{"label": "وزرة", "kind": "Length", "points": [[0, 0], [100, 0], [100, 50]]},
					],
				}
			)
			self.assertEqual([m["value"] for m in tk["measurements"]], [20.0, 3.0])
			self.assertEqual(tk["measurements"][0]["uom"], "م²")
			res = takeoff.push_to_estimate(tk["name"], tk["measurements"][0]["name"], line=est.lines[0].name)
			self.assertEqual(res["qty"], 20.0)
			new = takeoff.push_to_estimate(tk["name"], tk["measurements"][1]["name"])
		est.reload()
		self.assertEqual(est.lines[0].qty, 20)
		self.assertEqual([l.qty for l in est.lines if l.name == new["line"]], [3.0])
		# client-sent values are ignored: the server recomputes from the points
		with self.set_user(SALES):
			again = takeoff.save_takeoff(
				{
					**takeoff.get_takeoff(tk["name"]),
					"measurements": [
						{
							"label": "x",
							"kind": "Area",
							"points": [[0, 0], [50, 0], [50, 50], [0, 50]],
							"value": 999,
						}
					],
				}
			)
		self.assertEqual(again["measurements"][0]["value"], 1.0)
		est.submit()
		with self.set_user(SALES):
			self.assertRaises(
				frappe.ValidationError, takeoff.push_to_estimate, tk["name"], again["measurements"][0]["name"]
			)
		with self.set_user(make_world().users.eng1):
			self.assertRaises(frappe.PermissionError, takeoff.get_takeoff, tk["name"])
