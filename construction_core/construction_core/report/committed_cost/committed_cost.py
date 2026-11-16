"""التكلفة الملتزم بيها (phase 13): open purchase orders and active subcontracts, per project and stage.

- Purchase orders: submitted, not closed; for each item row, its net amount minus what was
  already billed on it.
- Subcontracts: active; contract value of each line minus the gross approved in claims.
- Actual cost (already invoiced) is in the "Project Financial Summary" report.
"""

import frappe
from frappe import _
from frappe.utils import flt

from construction_core.permissions import assert_project_access


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.project:
		assert_project_access(filters.project)
	columns = [
		{
			"fieldname": "project",
			"label": _("المشروع"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 180,
		},
		{
			"fieldname": "project_stage",
			"label": _("المرحلة"),
			"fieldtype": "Link",
			"options": "Project Stage",
			"width": 160,
		},
		{"fieldname": "source", "label": _("النوع"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "document",
			"label": _("المستند"),
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": 150,
		},
		{"fieldname": "party", "label": _("المورد / المقاول"), "fieldtype": "Data", "width": 160},
		{"fieldname": "committed", "label": _("ملتزم بيه"), "fieldtype": "Currency", "width": 140},
	]
	return columns, get_data(filters)


def get_data(filters) -> list[dict]:
	cond, args = "", []
	if filters.get("project"):
		cond = " and poi.project = %s"
		args.append(filters.project)
	rows = []
	for r in frappe.db.sql(
		f"""select poi.project, poi.project_stage, po.name, po.supplier_name,
			sum(greatest(poi.base_net_amount - poi.billed_amt * po.conversion_rate, 0)) as committed
		from `tabPurchase Order Item` poi join `tabPurchase Order` po on po.name = poi.parent
		where po.docstatus = 1 and po.status not in ('Closed', 'Completed') and ifnull(poi.project, '') != ''{cond}
		group by poi.project, poi.project_stage, po.name, po.supplier_name""",
		args,
		as_dict=True,
	):
		if flt(r.committed, 2):
			rows.append(
				{
					"project": r.project,
					"project_stage": r.project_stage,
					"source": _("أمر شراء"),
					"doctype": "Purchase Order",
					"document": r.name,
					"party": r.supplier_name,
					"committed": flt(r.committed, 2),
				}
			)
	sub_filters = {"docstatus": 1, "status": "Active"}
	if filters.get("project"):
		sub_filters["project"] = filters.project
	for s in frappe.get_all("Subcontract", filters=sub_filters, fields=["name", "project", "supplier"]):
		claimed = dict(
			frappe.db.sql(
				"""select l.subcontract_line, sum(l.amount) from `tabSubcontract Claim Line` l
				join `tabSubcontract Claim` c on c.name = l.parent
				where c.subcontract = %s and c.docstatus = 1 group by l.subcontract_line""",
				s.name,
			)
		)
		by_stage = {}
		for line in frappe.get_all(
			"Subcontract Line",
			filters={"parent": s.name, "parenttype": "Subcontract"},
			fields=["name", "project_stage", "amount"],
		):
			left = flt(line.amount) - flt(claimed.get(line.name))
			by_stage[line.project_stage] = flt(by_stage.get(line.project_stage, 0) + max(left, 0), 2)
		for stage, amount in by_stage.items():
			if amount:
				rows.append(
					{
						"project": s.project,
						"project_stage": stage,
						"source": _("عقد باطن"),
						"doctype": "Subcontract",
						"document": s.name,
						"party": s.supplier,
						"committed": amount,
					}
				)
	return rows
