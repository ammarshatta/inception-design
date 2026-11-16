"""Phase 2: share links, forced password change, no OAuth self-signup (P02-04, P02-06, P02-07)."""

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from construction_core import auth
from construction_core.api import admin
from construction_core.sharing import check_share_token
from construction_core.tests.factories import make_project


class TestShareLinks(IntegrationTestCase):
	def test_new_link_revokes_old(self):
		project = make_project("مشروع لينك المشاركة", [])
		first = admin.new_share_link(project)["url"].split("t=")[1]
		self.assertTrue(check_share_token(project, first))
		second = admin.new_share_link(project)["url"].split("t=")[1]
		self.assertTrue(check_share_token(project, second))
		self.assertFalse(check_share_token(project, first))
		self.assertFalse(check_share_token(project, "wrong"))
		self.assertFalse(check_share_token(project, None))
		self.assertEqual(frappe.db.get_value("Project", project, "visibility"), "link")
		self.assertNotIn(second, frappe.db.get_value("Project", project, "share_token_hash"))

	def test_expired_link(self):
		project = make_project("مشروع لينك منتهي", [])
		token = admin.new_share_link(project)["url"].split("t=")[1]
		frappe.db.set_value("Project", project, "share_expires_at", now_datetime() - timedelta(minutes=1))
		self.assertFalse(check_share_token(project, token))

	def test_private_project_link_fails(self):
		project = make_project("مشروع خاص", [])
		token = admin.new_share_link(project)["url"].split("t=")[1]
		frappe.db.set_value("Project", project, "visibility", "private")
		self.assertFalse(check_share_token(project, token))


class TestForcedPasswordChange(IntegrationTestCase):
	def test_allowed_paths(self):
		allowed = [
			"/update-password",
			"/assets/frappe/dist/js/x.js",
			"/api/method/frappe.core.doctype.user.user.update_password",
			"/api/method/logout",
		]
		blocked = [
			"/portal",
			"/app",
			"/api/method/construction_core.api.portal.get_me",
			"/api/resource/Project",
		]
		for path in allowed:
			self.assertTrue(auth.is_allowed_while_changing_password(path), path)
		for path in blocked:
			self.assertFalse(auth.is_allowed_while_changing_password(path), path)

	def test_flag_detection(self):
		self.assertFalse(auth.must_change_password("Administrator"))
		self.assertFalse(auth.must_change_password("Guest"))


class TestNoOAuthSignup(IntegrationTestCase):
	def test_login_settings_applied(self):
		self.assertEqual(frappe.db.get_single_value("Website Settings", "disable_signup"), 1)
		self.assertEqual(frappe.db.get_single_value("System Settings", "allow_login_using_user_name"), 1)
		self.assertEqual(frappe.db.get_single_value("System Settings", "allow_consecutive_login_attempts"), 5)

	def test_oauth_cannot_create_user(self):
		"""Frappe refuses when signup is disabled; our wrapper shows the Arabic message."""
		from frappe.utils.oauth import create_oauth_state, login_oauth_user

		email = "stranger.oauth@example.com"
		data = {"email": email, "given_name": "Stranger", "family_name": "OAuth", "email_verified": True}
		frappe.local.response = frappe._dict()
		auth._guarded(login_oauth_user, data, provider="google", state=create_oauth_state("/portal"))
		self.assertFalse(frappe.db.exists("User", email))
		self.assertEqual(frappe.local.response.get("http_status_code"), 403)
		self.assertEqual(frappe.local.message_title, auth.UNREGISTERED_MESSAGE)

	def test_guard_blocks_insert_during_oauth(self):
		frappe.flags.in_oauth_login = True
		try:
			user = frappe.get_doc({"doctype": "User", "email": "guard.oauth@example.com", "first_name": "x"})
			self.assertRaises(frappe.PermissionError, user.insert, ignore_permissions=True)
		finally:
			frappe.flags.in_oauth_login = False
		self.assertFalse(frappe.db.exists("User", "guard.oauth@example.com"))
