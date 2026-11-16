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
