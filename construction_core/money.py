"""Money flows (phase 6): milestone → Sales Invoice → Payment Entry, VAT template, item groups.

All amounts go through `flt(value, precision)`; ERPNext does the accounting.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

SERVICE_ITEM = "دفعة تعاقد"
SERVICE_ITEM_GROUP = "دفعات العملاء"
EXPENSE_ITEM_GROUPS = ("خامات", "عمالة", "معدات", "نقل")
VAT_ACCOUNT_NAME = "ضريبة القيمة المضافة"
VAT_TEMPLATE_TITLE = "ضريبة القيمة المضافة"


def _root_item_group() -> str:
	return (
		frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ["in", ["", None]]}, "name")
		or "All Item Groups"
	)


def ensure_item_groups():
	root = _root_item_group()
	for name in (*EXPENSE_ITEM_GROUPS, SERVICE_ITEM_GROUP):
		if not frappe.db.exists("Item Group", name):
			frappe.get_doc(
				{"doctype": "Item Group", "item_group_name": name, "parent_item_group": root, "is_group": 0}
			).insert(ignore_permissions=True)


def ensure_service_item():
	ensure_item_groups()
	if not frappe.db.exists("Item", SERVICE_ITEM):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": SERVICE_ITEM,
				"item_name": SERVICE_ITEM,
				"item_group": SERVICE_ITEM_GROUP,
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 0,
			}
		).insert(ignore_permissions=True)
	return SERVICE_ITEM


def ensure_vat_template(company: str) -> str | None:
	"""An Egyptian VAT template per company. The rate starts at 0: the accountant enters it."""
	if not company:
		return None
	existing = frappe.db.get_value(
		"Sales Taxes and Charges Template", {"company": company, "title": VAT_TEMPLATE_TITLE}, "name"
	)
	if existing:
		return existing
	parent = frappe.db.get_value(
		"Account", {"company": company, "account_type": "Tax", "is_group": 1}, "name"
	) or frappe.db.get_value("Account", {"company": company, "root_type": "Liability", "is_group": 1}, "name")
	if not parent:
		return None
	account = frappe.db.get_value("Account", {"company": company, "account_name": VAT_ACCOUNT_NAME}, "name")
	if not account:
		account = (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": VAT_ACCOUNT_NAME,
					"company": company,
					"parent_account": parent,
					"account_type": "Tax",
					"tax_rate": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	template = frappe.get_doc(
		{
			"doctype": "Sales Taxes and Charges Template",
			"title": VAT_TEMPLATE_TITLE,
			"company": company,
			"taxes": [
				{
					"charge_type": "On Net Total",
					"account_head": account,
					"description": VAT_TEMPLATE_TITLE,
					"rate": 0,
				}
			],
		}
	)
	template.insert(ignore_permissions=True)
	return template.name


def ensure_finance_setup():
	if not frappe.is_setup_complete():
		return
	ensure_item_groups()
	for company in frappe.get_all("Company", pluck="name"):
		ensure_vat_template(company)


def company_after_insert(doc, method=None):
	# Never let our extra setup break company creation (it runs inside the setup wizard).
	try:
		ensure_vat_template(doc.name)
	except Exception:
		frappe.log_error(title="construction_core: VAT template for new company")


# --- Milestone → invoice ---------------------------------------------------------------


def _can_invoice() -> bool:
	return bool(
		set(frappe.get_roles())
		& {"System Manager", "Construction Admin", "Accounts User", "Accounts Manager"}
	)


@frappe.whitelist(methods=["POST"])
def make_invoice(milestone: str) -> str:
	""" "اعمل فاتورة": a draft Sales Invoice for a Due milestone; the accountant reviews and submits it."""
	if not _can_invoice():
		frappe.throw(_("Only accounts or the office admin can invoice"), frappe.PermissionError)
	m = frappe.get_doc("Payment Milestone", milestone)
	m.check_permission("read")
	if m.status != "Due":
		frappe.throw(_("Only a Due milestone can be invoiced"))
	draft = frappe.db.get_value("Sales Invoice", {"payment_milestone": milestone, "docstatus": 0}, "name")
	if draft:
		return draft
	project = frappe.get_doc("Project", m.project)
	if not project.customer:
		frappe.throw(_("Set the project's customer first (Add Client)"))
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": project.company,
			"customer": project.customer,
			"project": project.name,
			"posting_date": nowdate(),
			"payment_milestone": milestone,
			"items": [
				{
					"item_code": ensure_service_item(),
					"item_name": _("دفعة: {0}").format(m.label),
					"description": _("دفعة: {0}").format(m.label),
					"qty": 1,
					"rate": flt(m.amount, 2),
				}
			],
		}
	)
	si.insert()
	return si.name


def sales_invoice_on_submit(doc, method=None):
	if doc.get("payment_milestone") and not doc.is_return:
		m = frappe.get_doc("Payment Milestone", doc.payment_milestone)
		m.sales_invoice = doc.name
		m.status = "Paid" if flt(doc.outstanding_amount, 2) <= 0 else "Invoiced"
		m.flags.ignore_permissions = True
		m.save()


def sales_invoice_on_cancel(doc, method=None):
	if doc.get("payment_milestone"):
		m = frappe.get_doc("Payment Milestone", doc.payment_milestone)
		if m.sales_invoice == doc.name:
			m.sales_invoice = None
			m.status = "Due"
			m.flags.ignore_permissions = True
			m.save()


def _sync_milestones_for_payment(doc):
	for ref in doc.references:
		if ref.reference_doctype != "Sales Invoice":
			continue
		milestone = frappe.db.get_value("Sales Invoice", ref.reference_name, "payment_milestone")
		if not milestone:
			continue
		si = frappe.db.get_value(
			"Sales Invoice", ref.reference_name, ["outstanding_amount", "docstatus"], as_dict=True
		)
		if si.docstatus != 1:
			continue
		status = "Paid" if flt(si.outstanding_amount, 2) <= 0 else "Invoiced"
		m = frappe.get_doc("Payment Milestone", milestone)
		if m.status != status:
			m.status = status
			m.flags.ignore_permissions = True
			m.save()


def payment_entry_on_submit(doc, method=None):
	_sync_milestones_for_payment(doc)


def payment_entry_on_cancel(doc, method=None):
	_sync_milestones_for_payment(doc)
