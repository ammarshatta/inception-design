# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class DesignTemplate(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not SLUG_RE.match(self.slug):
			frappe.throw(_("The slug may contain only lowercase English letters, digits and dashes"))
		if self.cost_from and self.cost_to and flt(self.cost_to) < flt(self.cost_from):
			frappe.throw(_("Cost to cannot be less than cost from"))
		self.sync_public_copies()

	def sync_public_copies(self):
		"""Public pages use only public copies; a published design gets them, an unpublished one loses them."""
		from construction_core.media import make_public_copy, remove_public_copy

		before = self.get_doc_before_save()
		old_cover = before.cover if before else None
		if self.cover_public and (not self.published or self.cover != old_cover):
			remove_public_copy(self.cover_public)
			self.cover_public = None
		if self.published and self.cover and not self.cover_public:
			self.cover_public = make_public_copy(self.cover, self.name or self.slug, "Design Template")
		for row in self.media:
			if row.public_file and not self.published:
				remove_public_copy(row.public_file)
				row.public_file = None
			elif self.published and row.file and not row.public_file:
				row.public_file = make_public_copy(row.file, self.name or self.slug, "Design Template")

	def on_trash(self):
		from construction_core.media import remove_public_copy

		for url in [self.cover_public, *[r.public_file for r in self.media]]:
			if url:
				remove_public_copy(url)
