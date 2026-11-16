"""Phase 3: engineer portal API, photo safety net, publishable copies (P03-01..P03-05)."""

import io
import os

import frappe
from frappe.tests import IntegrationTestCase
from PIL import Image

from construction_core.api import portal
from construction_core.media import MAX_PHOTO_BYTES
from construction_core.tests.factories import make_update, make_world, stages_of


def big_photo_with_gps() -> bytes:
	img = Image.frombytes("RGB", (2400, 1800), os.urandom(2400 * 1800 * 3))
	exif = Image.Exif()
	exif[0x010F] = "TestCam"
	gps = exif.get_ifd(0x8825)
	gps[1] = "N"
	gps[2] = (30.0, 2.0, 0.0)
	gps[3] = "E"
	gps[4] = (31.0, 14.0, 0.0)
	out = io.BytesIO()
	img.save(out, format="JPEG", quality=95, exif=exif)
	return out.getvalue()


class TestEngineerPortal(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		cls.s1 = stages_of(cls.w.p1)

	def test_my_projects_only_assigned(self):
		with self.set_user(self.w.users.eng1):
			names = [p.name for p in portal.my_projects()]
		self.assertIn(self.w.p1, names)
		self.assertNotIn(self.w.p2, names)

	def test_project_detail_other_project_denied(self):
		with self.set_user(self.w.users.eng1):
			self.assertRaises(frappe.PermissionError, portal.project_detail, self.w.p2)
			detail = portal.project_detail(self.w.p1)
		self.assertEqual(len(detail["stages"]), 8)
		self.assertTrue(detail["can_post"])

	def test_toggle_checklist_updates_progress(self):
		stage = self.s1[1]
		row = frappe.get_doc("Project Stage", stage).checklist[0]
		with self.set_user(self.w.users.eng1):
			res = portal.toggle_checklist_item(stage, row.name, 1)
		self.assertGreater(res["progress"], 0)
		self.assertGreater(res["project_progress"], 0)

	def test_client_cannot_post_or_tick(self):
		stage = self.s1[1]
		row = frappe.get_doc("Project Stage", stage).checklist[0]
		with self.set_user(self.w.users.client1):
			self.assertRaises(frappe.PermissionError, portal.create_stage_update, self.w.p1, stage, "x")
			self.assertRaises(frappe.PermissionError, portal.toggle_checklist_item, stage, row.name, 1)

	def test_client_stage_detail_hides_internal(self):
		stage = self.s1[2]
		internal = make_update(self.w.p1, stage, internal_only=1, text="internal note")
		public = make_update(self.w.p1, stage, internal_only=0, text="public note")
		with self.set_user(self.w.users.client1):
			names = [u.name for u in portal.stage_detail(stage)["updates"]]
		self.assertIn(public, names)
		self.assertNotIn(internal, names)

	def test_photo_is_resized_and_stripped(self):
		stage = self.s1[3]
		with self.set_user(self.w.users.eng1):
			update = portal.create_stage_update(self.w.p1, stage, "صور", None, 0)
		content = big_photo_with_gps()
		self.assertGreater(len(content), MAX_PHOTO_BYTES)
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "site.jpg",
				"content": content,
				"is_private": 1,
				"attached_to_doctype": "Stage Update",
				"attached_to_name": update,
			}
		).insert(ignore_permissions=True)
		self.assertTrue(file.is_private)
		with self.set_user(self.w.users.eng1):
			portal.attach_media(update, file.file_url, "Photo")
		path = frappe.get_doc("File", file.name).get_full_path()
		self.assertLessEqual(os.path.getsize(path), MAX_PHOTO_BYTES)
		with Image.open(path) as img:
			self.assertLessEqual(max(img.size), 1600)
			exif = img.getexif()
			self.assertFalse(exif.get_ifd(0x8825), "GPS data left in the photo")
		media = frappe.get_doc("Stage Update", update).media
		self.assertEqual(media[0].file, file.file_url)

	def test_attach_rejects_foreign_file(self):
		stage = self.s1[3]
		with self.set_user(self.w.users.eng1):
			update = portal.create_stage_update(self.w.p1, stage, "x", None, 0)
			self.assertRaises(
				frappe.ValidationError, portal.attach_media, update, "/private/files/nope.jpg", "Photo"
			)

	def test_publishable_makes_public_copy(self):
		stage = self.s1[4]
		with self.set_user(self.w.users.eng1):
			update = portal.create_stage_update(self.w.p1, stage, "للنشر", None, 0)
		img = Image.new("RGB", (800, 600), (200, 180, 160))
		out = io.BytesIO()
		img.save(out, format="JPEG")
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "pub.jpg",
				"content": out.getvalue(),
				"is_private": 1,
				"attached_to_doctype": "Stage Update",
				"attached_to_name": update,
			}
		).insert(ignore_permissions=True)
		with self.set_user(self.w.users.eng1):
			row = portal.attach_media(update, file.file_url, "Photo")["row"]
			portal.set_media_publishable(update, row, 1)
		media = frappe.get_doc("Stage Update", update).media[0]
		self.assertTrue(media.public_file)
		self.assertTrue(media.public_file.startswith("/files/"))
		self.assertEqual(frappe.db.get_value("File", {"file_url": media.public_file}, "is_private"), 0)
		self.assertTrue(media.file.startswith("/private/"))
		with self.set_user(self.w.users.eng1):
			portal.set_media_publishable(update, row, 0)
		self.assertFalse(frappe.get_doc("Stage Update", update).media[0].public_file)
		self.assertFalse(frappe.db.exists("File", {"file_url": media.public_file}))

	def test_pwa_manifest(self):
		from construction_core.api import public

		resp = public.manifest()
		self.assertEqual(resp.content_type, "application/manifest+json")
		self.assertIn(b"/portal/", resp.get_data())
		sw = public.service_worker()
		self.assertEqual(sw.headers["Service-Worker-Allowed"], "/portal/")
