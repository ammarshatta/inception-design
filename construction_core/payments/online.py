"""Paying milestones from the portal (phase 15).

Flow for a card or wallet:
1. `start_checkout` (client): an Online Payment (Pending) with our own reference, then the
   gateway checkout URL.
2. The gateway calls `api.public.paymob_webhook`: the HMAC is verified before anything else,
   then `reconcile` books it once (idempotent on the gateway transaction ID).
3. `sweep_pending` (every 15 minutes) asks the gateway about pending payments whose webhook
   never arrived.

Bank transfer / InstaPay: the client uploads the receipt (Awaiting Confirmation); an accountant
confirms it, which books it the same way.

Booking = the milestone's Sales Invoice (made and submitted if the milestone is still Due),
then a submitted Payment Entry against it; phase 6 marks the milestone Paid. A receipt PDF is
attached and emailed when an email account exists.
"""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, now_datetime, nowdate

from construction_core.payments.gateway import Transaction, get_gateway
from construction_core.permissions import assert_project_access, has_full_access, is_client
from construction_core.utils import as_system

PAYABLE = ("Due", "Invoiced")
ACCOUNTS = {"Accounts User", "Accounts Manager"}
RECEIPT_PRINT_FORMAT = "Inceptiondesign Receipt"


def _milestone_for_client(milestone: str):
	m = frappe.get_doc("Payment Milestone", milestone)
	assert_project_access(m.project)  # never trust the milestone sent by the browser
	m.check_permission("read")
	if m.status not in PAYABLE:
		frappe.throw(_("الدفعة دي مش مستحقة دلوقتي"))
	return m


def amount_due(m) -> Decimal:
	if m.sales_invoice and frappe.db.get_value("Sales Invoice", m.sales_invoice, "docstatus") == 1:
		return Decimal(str(frappe.db.get_value("Sales Invoice", m.sales_invoice, "outstanding_amount")))
	return Decimal(str(m.amount))


def _new_payment(m, method: str, **extra):
	amount = amount_due(m)
	if amount <= 0:
		frappe.throw(_("الدفعة دي متدفعة"))
	p = frappe.get_doc(
		{
			"doctype": "Online Payment",
			"project": m.project,
			"payment_milestone": m.name,
			"sales_invoice": m.sales_invoice,
			"amount": flt(amount, 2),
			"method": method,
			"title": _("دفعة: {0}").format(m.label),
			"paid_by": frappe.session.user,
			"reference": frappe.generate_hash(length=20),
			**extra,
		}
	)
	p.flags.ignore_permissions = True
	p.insert()
	return p


@frappe.whitelist(methods=["POST"])
def start_checkout(milestone: str, method: str = "Card") -> dict:
	if method not in ("Card", "Wallet"):
		frappe.throw(_("Unknown payment method"))
	m = _milestone_for_client(milestone)
	gw = get_gateway()
	p = _new_payment(m, method, gateway=gw.name, status="Pending")
	user = frappe.get_cached_doc("User", frappe.session.user)
	checkout = gw.create_checkout(
		p,
		{
			"first_name": user.first_name,
			"last_name": user.last_name,
			"email": None if (user.email or "").endswith(".invalid") else user.email,
			"phone": user.mobile_no,
		},
	)
	p.db_set({"checkout_url": checkout.url, "gateway_order_id": checkout.gateway_order_id})
	return {"payment": p.name, "url": checkout.url}


@frappe.whitelist(methods=["POST"])
def submit_transfer(milestone: str, method: str, file_url: str, note: str | None = None) -> dict:
	"""The client uploaded a bank transfer / InstaPay receipt (private, not attached yet)."""
	if method not in ("Bank Transfer", "InstaPay"):
		frappe.throw(_("Unknown payment method"))
	m = _milestone_for_client(milestone)
	file_name = frappe.db.get_value(
		"File",
		{
			"file_url": file_url,
			"owner": frappe.session.user,
			"is_private": 1,
			"attached_to_name": ["is", "not set"],
		},
		"name",
	)
	if not file_name:
		frappe.throw(_("The receipt photo was not found"))
	p = _new_payment(
		m, method, status="Awaiting Confirmation", proof_file=file_url, client_note=(note or "")[:500]
	)
	frappe.db.set_value(
		"File", file_name, {"attached_to_doctype": "Online Payment", "attached_to_name": p.name}
	)
	from construction_core.notifications import _notify

	_notify(accountants(), _("إيصال تحويل للمراجعة: {0}").format(p.title), "Online Payment", p.name)
	return {"payment": p.name, "status": p.status}


def accountants() -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"role": ["in", [*ACCOUNTS, "Construction Admin"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)


def _require_accounts():
	if not (has_full_access() or ACCOUNTS & set(frappe.get_roles())):
		frappe.throw(_("Only accounts can do this"), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def confirm_transfer(payment: str) -> str:
	_require_accounts()
	p = frappe.get_doc("Online Payment", payment)
	if p.status != "Awaiting Confirmation":
		frappe.throw(_("This payment is not waiting for confirmation"))
	p.db_set("confirmed_by", frappe.session.user)
	return book(p, transaction_id=None)


@frappe.whitelist(methods=["POST"])
def reject_transfer(payment: str, reason: str) -> None:
	_require_accounts()
	p = frappe.get_doc("Online Payment", payment)
	if p.status != "Awaiting Confirmation":
		frappe.throw(_("This payment is not waiting for confirmation"))
	p.db_set(
		{"status": "Rejected", "reject_reason": (reason or "")[:500], "confirmed_by": frappe.session.user}
	)
	from construction_core.notifications import _notify

	_notify([p.paid_by], _("الإيصال محتاج مراجعة: {0}").format(reason or ""), "Online Payment", p.name)


# --- Booking --------------------------------------------------------------------------


def _invoice_for(m) -> str:
	if m.sales_invoice and frappe.db.get_value("Sales Invoice", m.sales_invoice, "docstatus") == 1:
		return m.sales_invoice
	from construction_core.money import make_invoice

	name = make_invoice(m.name)
	si = frappe.get_doc("Sales Invoice", name)
	si.submit()
	return si.name


def _deposit_account(p) -> str | None:
	s = frappe.get_cached_doc("Inceptiondesign Settings")
	return s.gateway_clearing_account if p.method in ("Card", "Wallet") else s.manual_payment_account


def book(p, transaction_id: str | None, paid: Decimal | None = None) -> str:
	"""Create and submit the Payment Entry once. Locks the Online Payment row first."""
	frappe.db.sql("select name from `tabOnline Payment` where name=%s for update", p.name)
	p.reload()
	if p.payment_entry:
		return p.payment_entry
	with as_system():
		m = frappe.get_doc("Payment Milestone", p.payment_milestone)
		si = _invoice_for(m)
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		amount = flt(paid if paid is not None else p.amount, 2)
		pe = get_payment_entry("Sales Invoice", si, party_amount=amount)
		account = _deposit_account(p)
		if account:
			pe.paid_to = account
			pe.paid_to_account_currency = frappe.get_cached_value("Account", account, "account_currency")
		pe.paid_amount = amount
		pe.received_amount = amount
		pe.reference_no = transaction_id or p.name
		pe.reference_date = nowdate()
		pe.mode_of_payment = None
		pe.remarks = _("{0} — {1} ({2})").format(p.title, p.method, transaction_id or p.name)
		for ref in pe.references:
			ref.allocated_amount = min(flt(ref.outstanding_amount, 2), amount)
		pe.flags.ignore_permissions = True
		pe.insert()
		pe.submit()
		p.db_set(
			{
				"status": "Paid",
				"payment_entry": pe.name,
				"sales_invoice": si,
				"transaction_id": transaction_id,
				"amount": amount,
			}
		)
		send_receipt(p.name)
	return pe.name


def reconcile(tx: Transaction) -> str | None:
	"""Apply a verified gateway transaction. Safe to call any number of times."""
	if not tx.reference:
		return None
	name = frappe.db.get_value("Online Payment", {"reference": tx.reference}, "name")
	if not name:
		frappe.log_error(title="Payment: unknown reference", message=f"reference={tx.reference}")
		return None
	existing = frappe.db.get_value("Online Payment", {"transaction_id": tx.transaction_id}, "name")
	if existing and existing != name:
		return None
	p = frappe.get_doc("Online Payment", name)
	if p.payment_entry:
		return p.payment_entry  # duplicate notification
	if tx.pending:
		return None
	if not tx.success:
		p.db_set({"status": "Failed", "transaction_id": tx.transaction_id or None})
		return None
	return book(p, tx.transaction_id, tx.amount)


def sweep_pending():
	"""Every 15 minutes: ask the gateway about checkouts with no webhook yet."""
	s = frappe.get_cached_doc("Inceptiondesign Settings")
	if not s.enable_online_payments:
		return
	rows = frappe.get_all(
		"Online Payment",
		filters={
			"status": "Pending",
			"method": ["in", ["Card", "Wallet"]],
			"creation": ["<", add_to_date(now_datetime(), minutes=-2)],
		},
		pluck="name",
	)
	if not rows:
		return
	gw = get_gateway()
	for name in rows:
		p = frappe.get_doc("Online Payment", name)
		try:
			tx = gw.inquire(p)
			p.db_set("last_checked", now_datetime())
			if tx:
				reconcile(tx)
			elif p.creation < add_to_date(now_datetime(), days=-3):
				p.db_set("status", "Expired")
			if not frappe.flags.in_test:
				frappe.db.commit()  # one payment at a time
		except Exception:
			if not frappe.flags.in_test:
				frappe.db.rollback()
			frappe.log_error(title=f"Payment sweep: {name}")


@frappe.whitelist()
def payment_status(reference: str) -> dict:
	"""For the portal after the gateway redirects back. Checks the gateway once if still pending."""
	name = frappe.db.get_value("Online Payment", {"reference": reference}, "name")
	if not name:
		frappe.throw(_("Not found"), frappe.PermissionError)
	p = frappe.get_doc("Online Payment", name)
	assert_project_access(p.project)
	if p.status == "Pending" and p.method in ("Card", "Wallet"):
		try:
			tx = get_gateway().inquire(p)
			if tx:
				with as_system():
					reconcile(tx)
				p.reload()
		except Exception:
			frappe.log_error(title=f"Payment status check: {name}")
	return {"status": p.status, "milestone": p.payment_milestone}


# --- Receipts -------------------------------------------------------------------------


def send_receipt(payment: str):
	"""Attach the Arabic receipt PDF to the Online Payment and email it when possible."""
	p = frappe.get_doc("Online Payment", payment)
	try:
		pdf = frappe.get_print(
			"Payment Entry", p.payment_entry, print_format=RECEIPT_PRINT_FORMAT, as_pdf=True, no_letterhead=1
		)
	except Exception:
		frappe.log_error(title=f"Receipt PDF: {payment}")
		return
	email = frappe.db.get_value("User", p.paid_by, "email") if p.paid_by else None
	if (
		email
		and not email.endswith(".invalid")
		and frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1})
	):
		frappe.sendmail(
			recipients=[email],
			subject=_("إيصال دفع: {0}").format(p.title),
			message=_("استلمنا دفعتك بقيمة {0} ج.م. الإيصال مرفق. شكراً ليك.").format(flt(p.amount, 2)),
			attachments=[{"fname": f"{p.payment_entry}.pdf", "fcontent": pdf}],
			reference_doctype="Online Payment",
			reference_name=p.name,
			now=False,
		)
		p.db_set("receipt_sent", 1)


@frappe.whitelist()
def receipt_pdf(payment: str):
	from werkzeug.wrappers import Response

	p = frappe.get_doc("Online Payment", payment)
	assert_project_access(p.project)
	p.check_permission("read")
	if not p.payment_entry:
		frappe.throw(_("No receipt yet"), frappe.DoesNotExistError)
	with as_system():
		pdf = frappe.get_print(
			"Payment Entry", p.payment_entry, print_format=RECEIPT_PRINT_FORMAT, as_pdf=True, no_letterhead=1
		)
	resp = Response(pdf, content_type="application/pdf")
	resp.headers["Content-Disposition"] = f'attachment; filename="{p.payment_entry}.pdf"'
	return resp


@frappe.whitelist()
def project_payments(project: str) -> dict:
	assert_project_access(project)
	s = frappe.get_cached_doc("Inceptiondesign Settings")
	rows = frappe.get_all(
		"Online Payment",
		filters={"project": project},
		fields=["name", "payment_milestone", "amount", "method", "status", "creation", "payment_entry"],
		order_by="creation desc",
	)
	return {
		"online_enabled": bool(s.enable_online_payments),
		"card": bool(s.paymob_card_integration_id),
		"wallet": bool(s.paymob_wallet_integration_id),
		"bank_transfer_details": s.bank_transfer_details,
		"instapay_details": s.instapay_details,
		"payments": rows,
	}


# --- Refunds --------------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def refund(payment: str, note: str) -> dict:
	"""Accounts Manager only: refund at the gateway, then cancel the Payment Entry (ERPNext posts
	the reversing ledger entries and the invoice is open again), with the note on both records."""
	if "Accounts Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
		frappe.throw(_("Only an Accounts Manager can refund"), frappe.PermissionError)
	if not (note or "").strip():
		frappe.throw(_("Write the reason"))
	p = frappe.get_doc("Online Payment", payment)
	if p.status != "Paid" or not p.payment_entry:
		frappe.throw(_("Only a paid payment can be refunded"))
	refund_ref = None
	if p.method in ("Card", "Wallet"):
		refund_ref = get_gateway().refund(p, Decimal(str(p.amount)))
	note = note.strip()
	pe = frappe.get_doc("Payment Entry", p.payment_entry)
	pe.add_comment("Info", _("استرداد بواسطة {0}: {1}").format(frappe.session.user, note))
	pe.flags.ignore_permissions = True
	pe.cancel()  # phase 6 hook moves the milestone back to Invoiced
	p.db_set(
		{
			"status": "Refunded",
			"refund_note": note[:1000],
			"refunded_by": frappe.session.user,
			"refund_reference": refund_ref,
		}
	)
	p.add_comment("Info", _("استرداد بواسطة {0}: {1}").format(frappe.session.user, note))
	return {"payment_entry": pe.name, "refund_reference": refund_ref}
