"""Phase 5: public allowlist API, leak test, identical 404s, rate limit, demo content."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from construction_core.api import admin, public
from construction_core.setup import demo
from construction_core.tests.factories import make_project, make_world, stages_of

FORBIDDEN = ("phone", "mobile", "email", "amount", "customer", "internal_only", "/private/")


def assert_no_leak(testcase, payload, where):
	text = json.dumps(payload, ensure_ascii=False, default=str).lower()
	for word in FORBIDDEN:
		testcase.assertNotIn(word, text, f"'{word}' leaked from {where}: {text[:400]}")


class TestPublicSite(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		demo.install()

	def public_project(self):
		project = make_project("مشروع عام للتجربة", [self.w.users.client1])
		stage = stages_of(project)[0]
		doc = frappe.get_doc(
			{"doctype": "Stage Update", "project": project, "project_stage": stage, "text": "تحديث عام"}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Stage Update",
				"project": project,
				"project_stage": stage,
				"text": "سر داخلي",
				"internal_only": 1,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Project",
			project,
			{
				"visibility": "public",
				"slug": "public-test-project",
				"public_show_stages": 1,
				"public_show_photos": "all",
				"public_show_updates_text": 1,
				"public_location_level": "full",
				"public_show_client_name": 1,
				"area_label": "التجمع الخامس",
			},
		)
		return project, doc.name

	def test_leak_test_every_public_method(self):
		project, _upd = self.public_project()
		token = admin.new_share_link(project)["url"].split("t=")[1]
		frappe.db.set_value("Project", project, "visibility", "public")
		payloads = {
			"list_designs": public.list_designs(),
			"get_public_design": public.get_public_design(demo.DEMO_SLUG),
			"get_public_project(slug)": public.get_public_project(slug="public-test-project"),
			"get_public_project(token)": public.get_public_project(slug=project, token=token),
			"list_public_projects": public.list_public_projects(),
			"manifest": json.loads(public.manifest().get_data()),
			"sitemap": public.sitemap().get_data(as_text=True),
		}
		for where, payload in payloads.items():
			assert_no_leak(self, payload, where)
		p = payloads["get_public_project(slug)"]
		self.assertNotIn("سر داخلي", json.dumps(p, ensure_ascii=False))
		self.assertIn("تحديث عام", json.dumps(p, ensure_ascii=False))

	def test_identical_404s(self):
		project = make_project("مشروع خاص 404", [])
		token = admin.new_share_link(project)["url"].split("t=")[1]
		admin.new_share_link(project)  # revokes `token`
		frappe.db.set_value("Design Template", demo.DEMO_SLUG, "published", 1)
		cases = {
			"private project": lambda: public.get_public_project(slug="no-such-slug"),
			"revoked token": lambda: public.get_public_project(slug=project, token=token),
			"wrong token": lambda: public.get_public_project(slug=project, token="x"),
			"missing design": lambda: public.get_public_design("no-such-design"),
		}
		messages = set()
		for name, fn in cases.items():
			with self.assertRaises(public.NotFound, msg=name) as ctx:
				fn()
			messages.add(str(ctx.exception))
		self.assertEqual(len(messages), 1)

	def test_unpublished_design_404_and_public_copies_removed(self):
		doc = frappe.get_doc("Design Template", demo.DEMO_SLUG)
		self.assertTrue(doc.cover_public.startswith("/files/"))
		self.assertTrue(all(m.public_file.startswith("/files/") for m in doc.media))
		design = public.get_public_design(demo.DEMO_SLUG)
		self.assertEqual(len([m for m in design["media"] if m["kind"] == "Floor Plan"]), 1)
		self.assertEqual(len(design["stages"]), 6)
		doc.published = 0
		doc.save(ignore_permissions=True)
		self.assertFalse(doc.cover_public)
		self.assertRaises(public.NotFound, public.get_public_design, demo.DEMO_SLUG)
		doc.published = 1
		doc.save(ignore_permissions=True)

	def test_filters(self):
		res = public.list_designs(filters={"bedrooms": 3, "style": "مودرن"})
		self.assertIn(demo.DEMO_SLUG, [d["slug"] for d in res["designs"]])
		res = public.list_designs(filters={"bedrooms": 5})
		self.assertNotIn(demo.DEMO_SLUG, [d["slug"] for d in res["designs"]])
		res = public.list_designs(filters={"price_max": 100000})
		self.assertNotIn(demo.DEMO_SLUG, [d["slug"] for d in res["designs"]])

	def test_request_creates_lead(self):
		frappe.set_user("Guest")
		try:
			res = public.request_design(
				full_name="زائر تجربة",
				mobile="01011112222",
				governorate="القاهرة",
				apartment_area_m2=150,
				design=demo.DEMO_SLUG,
				consent=1,
			)
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(res["ok"])
		lead = frappe.get_all(
			"Lead", filters={"mobile_no": "01011112222"}, fields=["name", "design_template", "governorate"]
		)
		self.assertEqual(lead[0].design_template, demo.DEMO_SLUG)
		self.assertEqual(lead[0].governorate, "القاهرة")

	def test_request_validation_and_honeypot(self):
		self.assertRaises(
			frappe.ValidationError,
			public.request_design,
			"اسم",
			"0101",
			"القاهرة",
			None,
			None,
			None,
			None,
			None,
			1,
		)
		before = frappe.db.count("Lead")
		public.request_design("bot", "01011113333", "القاهرة", website="http://spam", consent=1)
		self.assertEqual(frappe.db.count("Lead"), before)

	def test_demo_remove(self):
		demo.remove()
		self.assertFalse(frappe.db.exists("Design Template", demo.DEMO_SLUG))
		self.assertFalse(
			frappe.db.exists(
				"File", {"attached_to_doctype": "Design Template", "attached_to_name": demo.DEMO_SLUG}
			)
		)
		demo.install()
