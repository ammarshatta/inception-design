# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from construction_core.costing import engine
from construction_core.costing.engine import D, round2


class Estimate(Document):
	def validate(self):
		if not self.customer and not self.lead:
			frappe.throw(_("Choose a customer or a lead"))
		if self.payment_terms and sum(D(t.percent) for t in self.payment_terms) != D(100):
			frappe.throw(_("Payment terms must add up to 100%"))
		self.recalculate()

	def before_submit(self):
		self.status = "Approved"

	def on_cancel(self):
		self.db_set("status", "Superseded")

	def governorate(self):
		if self.lead:
			return frappe.db.get_value("Lead", self.lead, "governorate")
		return None

	def recalculate(self):
		"""Draft: prices are looked up for the estimate date and captured into each line."""
		gov = self.governorate()
		all_parts = []
		for line in self.lines:
			parts = engine.line_parts(line, self.estimate_date, gov)
			line.material_part = round2(parts["Material"])
			line.labor_part = round2(parts["Labor"])
			line.equipment_part = round2(parts["Equipment"])
			line.other_part = round2(parts["Other"])
			line.unit_cost = round2(D(line.unit_cost)) if line.line_type != "Assembly" else D(line.unit_cost)
			all_parts.append(parts)
		res = engine.compute(
			all_parts, self.overhead_pct, self.profit_pct, engine.tax_rate(self.taxes_template)
		)
		for line, total in zip(self.lines, res["line_totals"], strict=True):
			line.line_total = total
		cats = res["categories"]
		self.material_total = round2(cats["Material"])
		self.labor_total = round2(cats["Labor"])
		self.equipment_total = round2(cats["Equipment"])
		self.other_total = round2(cats["Other"])
		self.subtotal = round2(res["subtotal"])
		self.overhead_amount = round2(res["overhead"])
		self.profit_amount = round2(res["profit"])
		self.tax_amount = round2(res["tax"])
		self.grand_total = res["grand_total"]
		return res

	def section_totals(self) -> dict:
		"""Section → share of the taxable total (subtotal + overhead + profit), rounded,
		with the rounding difference put on the last section so the sum is exact."""
		res = engine.compute(
			[
				{
					"Material": D(line.material_part),
					"Labor": D(line.labor_part),
					"Equipment": D(line.equipment_part),
					"Other": D(line.other_part),
				}
				for line in self.lines
			],
			self.overhead_pct,
			self.profit_pct,
			0,
		)
		factor = res["taxable"] / res["subtotal"] if res["subtotal"] else D(1)
		sections: dict = {}
		for line in self.lines:
			sections[line.section] = sections.get(line.section, D(0)) + D(line.line_total)
		out = {name: round2(amount * factor) for name, amount in sections.items()}
		if out:
			last = list(out)[-1]
			out[last] += round2(res["taxable"]) - sum(out.values(), D(0))
		return out
