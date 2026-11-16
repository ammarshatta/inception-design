"""Costing engine (phase 7). Decimal only; rounding to 2 places happens only on each
line total and on the final total.

Price lookups:
- materials and equipment: ERPNext `Item Price` on the buying price list, latest
  `valid_from` on or before the estimate date
- labour: `Labor Rate`, governorate-specific first, then any governorate
"""

from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _

BUYING_PRICE_LIST = "أسعار الخامات"
CENT = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")
CATEGORIES = ("Material", "Labor", "Equipment", "Other")


def D(value) -> Decimal:
	"""Decimal from a stored value (str() avoids binary floating-point artefacts)."""
	if value is None or value == "":
		return ZERO
	if isinstance(value, Decimal):
		return value
	return Decimal(str(value))


def round2(value: Decimal) -> Decimal:
	return value.quantize(CENT, rounding=ROUND_HALF_UP)


def ensure_price_list() -> str:
	if not frappe.db.exists("Price List", BUYING_PRICE_LIST):
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": BUYING_PRICE_LIST,
				"buying": 1,
				"selling": 0,
				"currency": frappe.db.get_default("currency") or "EGP",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
	return BUYING_PRICE_LIST


def material_price(item: str, on_date) -> Decimal:
	rows = frappe.get_all(
		"Item Price",
		filters={"item_code": item, "price_list": BUYING_PRICE_LIST, "valid_from": ["<=", on_date]},
		fields=["price_list_rate"],
		order_by="valid_from desc, creation desc",
		limit=1,
	)
	if not rows:
		frappe.throw(_("No price for {0} on {1}").format(item, on_date))
	return D(rows[0].price_list_rate)


def labor_price(labor_type: str, on_date, governorate: str | None = None) -> Decimal:
	for gov in ([governorate] if governorate else []) + [""]:
		filters = {"labor_type": labor_type, "valid_from": ["<=", on_date]}
		filters["governorate"] = gov if gov else ["is", "not set"]
		rows = frappe.get_all(
			"Labor Rate", filters=filters, fields=["rate"], order_by="valid_from desc, creation desc", limit=1
		)
		if rows:
			return D(rows[0].rate)
	frappe.throw(_("No labour rate for {0} on {1}").format(labor_type, on_date))


def _component_unit(line, on_date, governorate) -> tuple[str, Decimal]:
	"""(category, unit price) of one assembly component."""
	if line.line_type == "Labor":
		return "Labor", labor_price(line.labor_type, on_date, governorate)
	if line.line_type == "Other":
		return "Other", D(line.get("other_rate"))
	return line.line_type, material_price(line.item, on_date)


def assembly_unit_cost(assembly: str, on_date, governorate: str | None = None) -> dict[str, Decimal]:
	"""Cost of one unit of an assembly, by category: Σ(qty_per_unit × (1 + waste) × price)."""
	doc = frappe.get_cached_doc("Assembly", assembly)
	parts = dict.fromkeys(CATEGORIES, ZERO)
	for line in doc.items:
		category, price = _component_unit(line, on_date, governorate)
		parts[category] += D(line.qty_per_unit) * (1 + D(line.waste_pct) / HUNDRED) * price
	return parts


def line_parts(line, on_date, governorate: str | None = None) -> dict[str, Decimal]:
	"""Unrounded cost of an estimate line by category. Looks the price up for `on_date`
	and captures it into `line.unit_cost` (except type Other, which is typed in)."""
	qty = D(line.qty)
	waste = 1 + D(line.waste_pct) / HUNDRED
	parts = dict.fromkeys(CATEGORIES, ZERO)
	if line.line_type == "Assembly":
		unit_parts = assembly_unit_cost(line.assembly, on_date, governorate)
		for cat, unit in unit_parts.items():
			parts[cat] = qty * waste * unit
		line.unit_cost = sum(unit_parts.values(), ZERO)
		return parts
	if line.line_type in ("Material", "Equipment"):
		line.unit_cost = material_price(line.item, on_date)
	elif line.line_type == "Labor":
		line.unit_cost = labor_price(line.labor_type, on_date, governorate)
	parts[line.line_type] = qty * waste * D(line.unit_cost)
	return parts


def tax_rate(template: str | None) -> Decimal:
	if not template:
		return ZERO
	rows = frappe.get_all(
		"Sales Taxes and Charges",
		filters={
			"parenttype": "Sales Taxes and Charges Template",
			"parent": template,
			"charge_type": "On Net Total",
		},
		pluck="rate",
	)
	return sum((D(r) for r in rows), ZERO)


def compute(lines, overhead_pct, profit_pct, tax_pct) -> dict:
	"""Pure totals from already-computed line parts (each line: dict of category → Decimal).

	Line totals are rounded; category subtotals are not; overhead, profit and tax are
	applied in that order; only the final total is rounded again.
	"""
	cats = dict.fromkeys(CATEGORIES, ZERO)
	line_totals = []
	for parts in lines:
		for cat, value in parts.items():
			cats[cat] += value
		line_totals.append(round2(sum(parts.values(), ZERO)))
	subtotal = sum(line_totals, ZERO)
	overhead = subtotal * D(overhead_pct) / HUNDRED
	profit = (subtotal + overhead) * D(profit_pct) / HUNDRED
	taxable = subtotal + overhead + profit
	tax = taxable * D(tax_pct) / HUNDRED
	return {
		"line_totals": line_totals,
		"categories": cats,
		"subtotal": subtotal,
		"overhead": overhead,
		"profit": profit,
		"taxable": taxable,
		"tax": tax,
		"grand_total": round2(taxable + tax),
	}
