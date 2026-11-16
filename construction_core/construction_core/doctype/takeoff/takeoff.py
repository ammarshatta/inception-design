# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from construction_core import takeoff


class Takeoff(Document):
	def validate(self):
		takeoff.compute(self)
