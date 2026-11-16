"""Subcontracts and progress claims (مستخلصات), phase 13.

Math, all in Decimal and rounded only on the stored totals:
- gross            = Σ current_qty × rate
- retention        = gross × retention_pct ÷ 100
- advance recovery = advance × gross ÷ contract value, capped at what is still unrecovered;
                     the claim that completes the contract recovers the whole remainder
- net due          = gross − retention − advance recovery

Approving (submitting) a claim books a Purchase Invoice: the expense is the gross; the
retention goes to the "محتجزات مقاولين الباطن" liability account and the advance recovery to
the "سلف مقاولين الباطن" asset account, as deductions; the supplier is owed the net.
"""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from construction_core.costing.engine import D, round2
from construction_core.permissions import assert_project_access, has_full_access

RETENTION_ACCOUNT = "محتجزات مقاولين الباطن"
ADVANCE_ACCOUNT = "سلف مقاولين الباطن"
SUBCONTRACT_ITEM = "أعمال مقاولين الباطن"
SUPPLIER_GROUPS = ("مقاولين باطن", "موردين خامات")


# --- Setup ----------------------------------------------------------------------------


def ensure_supplier_groups():
	root = frappe.db.get_value("Supplier Group", {"is_group": 1, "parent_supplier_group": ["in", ["", None]]})
	for name in SUPPLIER_GROUPS:
		if not frappe.db.exists("Supplier Group", name):
			frappe.get_doc(
				{"doctype": "Supplier Group", "supplier_group_name": name, "parent_supplier_group": root}
			).insert(ignore_permissions=True)


def _group_account(company: str, root_type: str, names: tuple) -> str:
	for n in names:
		acc = frappe.db.get_value(
			"Account", {"company": company, "is_group": 1, "root_type": root_type, "account_name": n}, "name"
		)
		if acc:
			return acc
	return frappe.db.get_value(
		"Account", {"company": company, "is_group": 1, "root_type": root_type}, "name", order_by="lft desc"
	)


def ensure_account(company: str, kind: str) -> str:
	if kind == "retention":
		name, root, groups = RETENTION_ACCOUNT, "Liability", ("Current Liabilities", "الخصوم المتداولة")
	else:
		name, root, groups = ADVANCE_ACCOUNT, "Asset", ("Loans and Advances (Assets)", "Current Assets")
	existing = frappe.db.get_value("Account", {"company": company, "account_name": name}, "name")
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": name,
				"company": company,
				"parent_account": _group_account(company, root, groups),
				"root_type": root,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def ensure_subcontract_item() -> str:
	from construction_core.money import ensure_item_groups

	ensure_item_groups()
	if not frappe.db.exists("Item", SUBCONTRACT_ITEM):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": SUBCONTRACT_ITEM,
				"item_name": SUBCONTRACT_ITEM,
				"item_group": "عمالة",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 0,
				"is_purchase_item": 1,
			}
		).insert(ignore_permissions=True)
	return SUBCONTRACT_ITEM


def ensure_procurement_setup():
	if not frappe.is_setup_complete():
		return
	ensure_supplier_groups()
	ensure_subcontract_item()
	for company in frappe.get_all("Company", pluck="name"):
		ensure_account(company, "retention")
		ensure_account(company, "advance")


# --- Subcontract ----------------------------------------------------------------------


def _require_admin():
	if not has_full_access():
		frappe.throw(_("Only the office admin can do this"), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def send_for_signature(subcontract: str) -> dict:
	"""Render the subcontract and send it to the subcontractor's portal user for e-signature."""
	_require_admin()
	from construction_core.esign import create_signature_request, signing_links

	doc = frappe.get_doc("Subcontract", subcontract)
	if doc.docstatus != 0:
		frappe.throw(_("The subcontract is already signed"))
	if not doc.signer_user:
		frappe.throw(_("Set the subcontractor's portal user first"))
	doc.save()  # validate the numbers before rendering
	req = create_signature_request(
		"Subcontract",
		doc.name,
		doc.signer_user,
		_("عقد مقاولة باطن: {0}").format(doc.title),
		project=doc.project,
	)
	doc.db_set({"signature_request": req.name, "status": "Awaiting Signature"})
	return signing_links(req)


def on_signed(req) -> str:
	doc = frappe.get_doc("Subcontract", req.reference_name)
	activate(doc)
	return doc.project


def activate(doc):
	"""Signed: submit, so the lines, rates and terms can no longer change."""
	doc.flags.signed = True
	doc.flags.ignore_permissions = True
	doc.status = "Active"
	doc.submit()


@frappe.whitelist(methods=["POST"])
def pay_advance(subcontract: str) -> str:
	"""Book the advance: Dr سلف مقاولين الباطن / Cr cash."""
	_require_admin()
	doc = frappe.get_doc("Subcontract", subcontract)
	if doc.docstatus != 1:
		frappe.throw(_("Sign the subcontract first"))
	if doc.advance_journal_entry:
		return doc.advance_journal_entry
	amount = flt(doc.advance_amount, 2)
	if amount <= 0:
		frappe.throw(_("No advance on this subcontract"))
	je = _journal_entry(
		doc.company,
		_("دفعة مقدمة: {0}").format(doc.title),
		[
			{"account": ensure_account(doc.company, "advance"), "debit_in_account_currency": amount},
			{"account": _cash_account(doc.company), "credit_in_account_currency": amount},
		],
		doc.project,
	)
	doc.db_set("advance_journal_entry", je)
	return je


def _cash_account(company: str) -> str:
	acc = frappe.get_cached_value("Company", company, "default_cash_account") or frappe.db.get_value(
		"Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name"
	)
	if not acc:
		frappe.throw(_("Set the company's default cash account"))
	return acc


def _journal_entry(company: str, remark: str, accounts: list, project: str | None = None) -> str:
	for a in accounts:
		a.setdefault("project", project)
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": company,
			"posting_date": nowdate(),
			"voucher_type": "Journal Entry",
			"user_remark": remark,
			"accounts": accounts,
		}
	)
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def subcontract_totals(subcontract: str) -> dict:
	"""Claimed, retention held, advance recovered, net invoiced and paid, from approved claims."""
	row = frappe.db.sql(
		"""select ifnull(sum(gross), 0), ifnull(sum(retention_amount), 0),
			ifnull(sum(advance_recovery), 0), ifnull(sum(net_due), 0)
		from `tabSubcontract Claim` where subcontract = %s and docstatus = 1""",
		subcontract,
	)[0]
	paid = frappe.db.sql(
		"""select ifnull(sum(pi.grand_total - pi.outstanding_amount), 0)
		from `tabPurchase Invoice` pi join `tabSubcontract Claim` c on c.purchase_invoice = pi.name
		where c.subcontract = %s and c.docstatus = 1 and pi.docstatus = 1""",
		subcontract,
	)[0][0]
	return frappe._dict(
		claimed=flt(row[0], 2),
		retention=flt(row[1], 2),
		advance_recovered=flt(row[2], 2),
		net=flt(row[3], 2),
		paid=flt(paid, 2),
	)


@frappe.whitelist(methods=["POST"])
def release_retention(subcontract: str) -> dict:
	"""End of works: move the held retention to the supplier (journal entry), then pay it."""
	if not (has_full_access() or "Accounts Manager" in frappe.get_roles()):
		frappe.throw(_("Only accounts or the office admin can release retention"), frappe.PermissionError)
	doc = frappe.get_doc("Subcontract", subcontract)
	if doc.docstatus != 1:
		frappe.throw(_("Sign the subcontract first"))
	if doc.retention_payment:
		frappe.throw(_("Retention was already released"))
	held = subcontract_totals(doc.name).retention
	if held <= 0:
		frappe.throw(_("No retention is held on this subcontract"))
	payable = frappe.get_cached_value("Company", doc.company, "default_payable_account")
	je = _journal_entry(
		doc.company,
		_("صرف المحتجز: {0}").format(doc.title),
		[
			{"account": ensure_account(doc.company, "retention"), "debit_in_account_currency": held},
			{
				"account": payable,
				"party_type": "Supplier",
				"party": doc.supplier,
				"credit_in_account_currency": held,
			},
		],
		doc.project,
	)
	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Pay",
			"company": doc.company,
			"posting_date": nowdate(),
			"party_type": "Supplier",
			"party": doc.supplier,
			"paid_from": _cash_account(doc.company),
			"paid_to": payable,
			"paid_amount": held,
			"received_amount": held,
			"project": doc.project,
			"remarks": _("صرف المحتجز: {0}").format(doc.title),
		}
	)
	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.submit()
	doc.db_set({"retention_release_entry": je, "retention_payment": pe.name, "status": "Completed"})
	return {"journal_entry": je, "payment_entry": pe.name, "amount": held}


# --- Claims ---------------------------------------------------------------------------


def previous_quantities(subcontract: str, exclude: str | None = None) -> dict:
	"""Approved quantities so far, per subcontract line."""
	rows = frappe.db.sql(
		"""select l.subcontract_line, sum(l.current_qty)
		from `tabSubcontract Claim Line` l join `tabSubcontract Claim` c on c.name = l.parent
		where c.subcontract = %s and c.docstatus = 1 and c.name != %s
		group by l.subcontract_line""",
		(subcontract, exclude or ""),
	)
	return {r[0]: D(r[1]) for r in rows}


def advance_recovered(subcontract: str, exclude: str | None = None) -> Decimal:
	return D(
		frappe.db.sql(
			"""select ifnull(sum(advance_recovery), 0) from `tabSubcontract Claim`
			where subcontract = %s and docstatus = 1 and name != %s""",
			(subcontract, exclude or ""),
		)[0][0]
	)


def compute_claim(sub, lines: list, previous: dict, recovered: Decimal) -> dict:
	"""Pure math for one claim. `lines`: dicts with subcontract_line and current_qty."""
	by_line = {l.name: l for l in sub.lines}
	out_lines, gross, over, complete = [], D(0), [], True
	current = {l["subcontract_line"]: D(l.get("current_qty") or 0) for l in lines}
	for line in sub.lines:
		prev = previous.get(line.name, D(0))
		cur = current.get(line.name, D(0))
		cumulative = prev + cur
		amount = round2(cur * D(line.rate))
		if cumulative > D(line.qty):
			over.append(line.description)
		if cumulative < D(line.qty):
			complete = False
		gross += amount
		out_lines.append(
			{
				"subcontract_line": line.name,
				"description": line.description,
				"project_stage": line.project_stage,
				"contract_qty": flt(line.qty),
				"rate": flt(line.rate, 2),
				"previous_qty": flt(prev),
				"current_qty": flt(cur),
				"cumulative_qty": flt(cumulative),
				"amount": flt(amount, 2),
			}
		)
	for key in current:
		if key not in by_line:
			frappe.throw(_("A claim line does not belong to this subcontract"))
	gross = round2(gross)
	retention = round2(gross * D(sub.retention_pct) / D(100))
	advance = D(sub.advance_amount)
	remaining = max(advance - recovered, D(0))
	contract_value = D(sub.contract_value)
	if complete:
		recovery = remaining
	else:
		recovery = round2(advance * gross / contract_value) if contract_value else D(0)
		recovery = min(recovery, remaining)
	return {
		"lines": out_lines,
		"gross": gross,
		"retention_amount": retention,
		"advance_recovery": recovery,
		"net_due": gross - retention - recovery,
		"over": over,
	}


@frappe.whitelist()
def new_claim(subcontract: str) -> dict:
	"""Lines for the next claim with the previous quantities filled in."""
	sub = frappe.get_doc("Subcontract", subcontract)
	assert_project_access(sub.project)
	if sub.docstatus != 1:
		frappe.throw(_("Sign the subcontract first"))
	previous = previous_quantities(subcontract)
	result = compute_claim(sub, [], previous, advance_recovered(subcontract))
	return {"subcontract": subcontract, "lines": result["lines"]}


def make_claim_invoice(claim) -> str:
	sub = frappe.get_doc("Subcontract", claim.subcontract)
	item = ensure_subcontract_item()
	taxes = []
	if flt(claim.retention_amount, 2):
		taxes.append(
			{
				"category": "Total",
				"add_deduct_tax": "Deduct",
				"charge_type": "Actual",
				"account_head": ensure_account(sub.company, "retention"),
				"description": _("محتجز {0}%").format(flt(sub.retention_pct)),
				"tax_amount": flt(claim.retention_amount, 2),
			}
		)
	if flt(claim.advance_recovery, 2):
		taxes.append(
			{
				"category": "Total",
				"add_deduct_tax": "Deduct",
				"charge_type": "Actual",
				"account_head": ensure_account(sub.company, "advance"),
				"description": _("استرداد دفعة مقدمة"),
				"tax_amount": flt(claim.advance_recovery, 2),
			}
		)
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": sub.company,
			"supplier": sub.supplier,
			"project": sub.project,
			"posting_date": nowdate(),
			"bill_no": claim.name,
			"subcontract_claim": claim.name,
			"disable_rounded_total": 1,
			"items": [
				{
					"item_code": item,
					"item_name": f"{l.description}"[:140],
					"description": _("مستخلص {0}: {1}").format(claim.claim_no, l.description),
					"qty": flt(l.current_qty),
					"rate": flt(l.rate, 2),
					"project": sub.project,
					"project_stage": l.project_stage,
				}
				for l in claim.lines
				if flt(l.current_qty)
			],
			"taxes": taxes,
		}
	)
	pi.flags.ignore_permissions = True
	pi.insert()
	pi.submit()
	return pi.name


@frappe.whitelist()
def subcontract_status(project: str | None = None) -> list[dict]:
	assert_project_access(project) if project else _require_admin()
	filters = {"docstatus": 1}
	if project:
		filters["project"] = project
	out = []
	for s in frappe.get_all(
		"Subcontract",
		filters=filters,
		fields=["name", "title", "supplier", "project", "contract_value", "status"],
		order_by="creation asc",
	):
		t = subcontract_totals(s.name)
		out.append({**s, **t})
	return out
