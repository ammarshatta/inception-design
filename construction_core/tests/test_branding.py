"""Branding lives only in Inceptiondesign Settings (P01-05, CLAUDE.md rule 15)."""

import re
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

from construction_core.branding import get_branding, get_feature_flags

APP_ROOT = Path(frappe.get_app_path("construction_core")).parent
SCANNED_SUFFIXES = {".py", ".html", ".js", ".ts", ".vue", ".json", ".md"}
SKIPPED_DIRS = {"node_modules", "tests", "public/frontend", ".git", "docs", "e2e/"}
EGYPT_MOBILE = re.compile(r"(?<!\d)01[0125]\d{8}(?!\d)")


def code_files():
	for path in APP_ROOT.rglob("*"):
		rel = path.relative_to(APP_ROOT).as_posix()
		if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
			continue
		if any(part in rel for part in SKIPPED_DIRS):
			continue
		yield path, rel


class TestBranding(IntegrationTestCase):
	def test_branding_reads_settings(self):
		settings = frappe.get_single("Inceptiondesign Settings")
		original = (settings.office_name, settings.primary_color)
		try:
			settings.office_name = "مكتب تجربة البراند"
			settings.primary_color = "#123456"
			settings.save(ignore_permissions=True)
			branding = get_branding()
			self.assertEqual(branding["office_name"], "مكتب تجربة البراند")
			self.assertEqual(branding["primary_color"], "#123456")
			self.assertIn("enable_selections", get_feature_flags())
		finally:
			settings.reload()
			settings.office_name, settings.primary_color = original
			settings.save(ignore_permissions=True)

	def test_no_hardcoded_office_name_or_phone(self):
		"""Fails if the configured office name or an Egyptian mobile number is in the code."""
		office_name = (frappe.db.get_single_value("Inceptiondesign Settings", "office_name") or "").strip()
		offenders = []
		for path, rel in code_files():
			text = path.read_text(errors="ignore")
			if office_name and office_name in text:
				offenders.append(f"{rel}: office name")
			if EGYPT_MOBILE.search(text):
				offenders.append(f"{rel}: phone number")
		self.assertEqual(offenders, [], "Hardcoded branding found: " + ", ".join(offenders))
