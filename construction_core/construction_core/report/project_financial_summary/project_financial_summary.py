"""ملخص مالي للمشروع (phase 6, task 5).

Every figure is read from submitted ERPNext documents, so it matches the General Ledger:
- contract value: sum of the project's payment milestones
- invoiced: submitted Sales Invoices with this project (grand total after VAT, or the rounded
  total when ERPNext rounding is on: that is what the receivable carries)
- collected: invoiced − outstanding
- outstanding: sum of the invoices' outstanding amounts (Accounts Receivable)
- expenses: submitted Purchase Invoice items (net, before tax) by item group and by stage
- budget vs actual: Project.estimated_costing vs expenses
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.project:
		frappe.throw(_("Choose a project"))
	frappe.get_doc("Project", filters.project).check_permission("read")
	summary = get_summary(filters.project)
	columns = [
		{"fieldname": "section", "label": _("القسم"), "fieldtype": "Data", "width": 160},
		{"fieldname": "label", "label": _("البند"), "fieldtype": "Data", "width": 260},
		{"fieldname": "amount", "label": _("المبلغ"), "fieldtype": "Currency", "width": 160},
	]
	data = [
		{"section": _("الإيرادات"), "label": _("قيمة العقد (الدفعات)"), "amount": summary.contract_value},
		{"section": _("الإيرادات"), "label": _("المفوتر"), "amount": summary.invoiced},
		{"section": _("الإيرادات"), "label": _("المحصّل"), "amount": summary.collected},
		{"section": _("الإيرادات"), "label": _("المتبقي على العميل"), "amount": summary.outstanding},
	]
	for group, amount in summary.expenses_by_group.items():
		data.append({"section": _("المصروفات حسب النوع"), "label": group or _("بدون نوع"), "amount": amount})
	for stage, amount in summary.expenses_by_stage.items():
		data.append(
			{"section": _("المصروفات حسب المرحلة"), "label": stage or _("بدون مرحلة"), "amount": amount}
		)
	data += [
		{"section": _("التكلفة"), "label": _("الميزانية"), "amount": summary.budget},
		{"section": _("التكلفة"), "label": _("المصروف الفعلي"), "amount": summary.expenses},
		{
			"section": _("التكلفة"),
			"label": _("الفرق (ميزانية − فعلي)"),
			"amount": flt(summary.budget - summary.expenses, 2),
		},
	]
	chart = {
		"data": {
			"labels": [_("العقد"), _("المفوتر"), _("المحصّل"), _("المصروف")],
			"datasets": [
				{"values": [summary.contract_value, summary.invoiced, summary.collected, summary.expenses]}
			],
		},
		"type": "bar",
	}
	return columns, data, None, chart


def get_summary(project: str) -> frappe._dict:
	precision = 2
	contract_value = flt(
		frappe.db.sql("select ifnull(sum(amount), 0) from `tabPayment Milestone` where project=%s", project)[
			0
		][0],
		precision,
	)
	si = frappe.db.sql(
		"""select ifnull(sum(if(disable_rounded_total = 1 or base_rounded_total = 0,
			base_grand_total, base_rounded_total)), 0), ifnull(sum(outstanding_amount), 0)
		from `tabSales Invoice` where project=%s and docstatus=1""",
		project,
	)[0]
	invoiced = flt(si[0], precision)
	outstanding = flt(si[1], precision)
	rows = frappe.db.sql(
		"""select pii.item_group, pi.project_stage, sum(pii.base_net_amount) as amount
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and ifnull(pii.project, pi.project) = %s
		group by pii.item_group, pi.project_stage""",
		project,
		as_dict=True,
	)
	by_group, by_stage = {}, {}
	stage_names = dict(
		frappe.get_all(
			"Project Stage", filters={"project": project}, fields=["name", "stage_name"], as_list=True
		)
	)
	for r in rows:
		by_group[r.item_group] = flt(by_group.get(r.item_group, 0) + flt(r.amount), precision)
		stage = stage_names.get(r.project_stage, r.project_stage)
		by_stage[stage] = flt(by_stage.get(stage, 0) + flt(r.amount), precision)
	expenses = flt(sum(by_group.values()), precision)
	return frappe._dict(
		contract_value=contract_value,
		invoiced=invoiced,
		collected=flt(invoiced - outstanding, precision),
		outstanding=outstanding,
		expenses_by_group=by_group,
		expenses_by_stage=by_stage,
		expenses=expenses,
		budget=flt(frappe.db.get_value("Project", project, "estimated_costing"), precision),
	)
