"""E-signature (phase 8): simple electronic signature with a strong audit trail.

Flow: send_for_signature → client views → request_otp (6 digits, emailed, 10 minutes,
stored hashed, 3 attempts) → sign (drawn signature) → signed PDF (original pages +
signature page) frozen with SHA-256 hashes → kickoff (project, stages, tasks, milestones).

Legal note: this is not an ITIDA-licensed signature (Egyptian Law 15/2004). See
docs/plan/phase-08-proposals-esign.md. `PROVIDER_HOOK` is where a licensed provider plugs in.
"""

import hashlib
import hmac
import io
import secrets
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, get_url, now_datetime

from construction_core.branding import get_branding
from construction_core.costing.engine import D, round2
from construction_core.permissions import has_full_access

CONTRACT_PRINT_FORMAT = "Inceptiondesign Contract"
SIGNATURE_PAGE_FORMAT = "Inceptiondesign Signature Page"
DEFAULT_TEMPLATE = "عقد تشطيب (افتراضي)"
OTP_MINUTES = 10
MAX_ATTEMPTS = 3
PROVIDER_HOOK = "construction_core_esign_provider"  # hooks.py key for a licensed provider (later)

DEFAULT_BODY = """<h2 style="text-align:center">عقد أعمال تشطيب</h2>
<p>تحرر هذا العقد بتاريخ {{ today }} بين <b>{{ branding.office_name or doc.company }}</b> (الطرف الأول)
و <b>{{ party_name }}</b> (الطرف الثاني)، على تنفيذ أعمال التشطيب الموضحة أدناه.</p>
<h3>الأعمال وقيمتها</h3>
<table style="width:100%;border-collapse:collapse">
<tr style="background:#E3F0EB"><th style="border:1px solid #C9CFC9;padding:6px;text-align:right">القسم</th><th style="border:1px solid #C9CFC9;padding:6px">القيمة</th></tr>
{% for name, amount in sections %}<tr><td style="border:1px solid #C9CFC9;padding:6px">{{ name }}</td><td style="border:1px solid #C9CFC9;padding:6px;text-align:center" dir="ltr">{{ "{:,.2f}".format(amount) }}</td></tr>{% endfor %}
{% if doc.tax_amount %}<tr><td style="border:1px solid #C9CFC9;padding:6px">الضرائب</td><td style="border:1px solid #C9CFC9;padding:6px;text-align:center" dir="ltr">{{ "{:,.2f}".format(doc.tax_amount) }}</td></tr>{% endif %}
<tr style="font-weight:bold"><td style="border:1px solid #C9CFC9;padding:6px">الإجمالي</td><td style="border:1px solid #C9CFC9;padding:6px;text-align:center" dir="ltr">{{ "{:,.2f}".format(doc.grand_total) }}</td></tr>
</table>
{% if terms %}<h3>الدفعات</h3>
<ol>{% for t in terms %}<li>{{ t.label }}: {{ t.percent }}% ({{ "{:,.2f}".format(t.amount) }}){% if t.after_section %} — بعد انتهاء {{ t.after_section }}{% endif %}</li>{% endfor %}</ol>{% endif %}
<h3>شروط عامة</h3>
<ol>
<li>أي تعديل على الأعمال بيتم بأمر تغيير مكتوب وموقّع من الطرفين.</li>
<li>الطرف الثاني بيتابع التنفيذ والصور والدفعات من بوابة العملاء.</li>
<li>{{ branding_terms }}</li>
</ol>"""


def ensure_contract_template():
	if not frappe.db.exists("Contract Template", DEFAULT_TEMPLATE):
		frappe.get_doc(
			{
				"doctype": "Contract Template",
				"title": DEFAULT_TEMPLATE,
				"applies_to": "Contract",
				"body": DEFAULT_BODY,
			}
		).insert(ignore_permissions=True)


def sha256(content: bytes) -> str:
	return hashlib.sha256(content).hexdigest()


def _request_info() -> tuple[str, str]:
	req = getattr(frappe.local, "request", None)
	ip = getattr(frappe.local, "request_ip", None) or ""
	ua = req.headers.get("User-Agent", "")[:500] if req else ""
	return ip, ua


def _event(doc, event: str, note: str | None = None):
	ip, ua = _request_info()
	doc.append(
		"events",
		{
			"event": event,
			"at": now_datetime(),
			"user": frappe.session.user,
			"ip": ip,
			"user_agent": ua,
			"note": note,
		},
	)


# --- Rendering ------------------------------------------------------------------------


def contract_context(doc) -> dict:
	sections = list(doc.section_totals().items()) if hasattr(doc, "section_totals") else []
	terms = []
	if doc.get("payment_terms"):
		amounts = term_amounts(doc)
		for t, amount in zip(doc.payment_terms, amounts, strict=True):
			terms.append(
				{"label": t.label, "percent": t.percent, "after_section": t.after_section, "amount": amount}
			)
	party_name = (
		frappe.db.get_value("Customer", doc.customer, "customer_name")
		if doc.get("customer")
		else frappe.db.get_value("Lead", doc.get("lead"), "lead_name")
	)
	settings = frappe.get_cached_doc("Inceptiondesign Settings")
	return {
		"doc": doc,
		"branding": get_branding(),
		"sections": sections,
		"terms": terms,
		"party_name": party_name or "",
		"today": frappe.utils.formatdate(frappe.utils.nowdate(), "dd-MM-yyyy"),
		"branding_terms": frappe.utils.strip_html(settings.terms_text or "")
		or "الشروط التفصيلية حسب الاتفاق.",
	}


def render_contract_body(doc) -> str:
	"""Jinja method used by the contract print format."""
	template = doc.get("contract_template") or DEFAULT_TEMPLATE
	body = frappe.db.get_value("Contract Template", template, "body") or DEFAULT_BODY
	return frappe.render_template(body, contract_context(doc))


def term_amounts(doc) -> list:
	"""Payment term amounts from the grand total; the last one takes the rounding difference."""
	total = D(doc.grand_total)
	amounts = [round2(total * D(t.percent) / 100) for t in doc.payment_terms]
	if amounts:
		amounts[-1] += total - sum(amounts, D(0))
	return amounts


def _save_private_file(name: str, content: bytes, docname: str, field: str) -> str:
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": name,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Signature Request",
			"attached_to_name": docname,
			"attached_to_field": field,
		}
	)
	f.flags.ignore_permissions = True
	f.insert()
	return f.file_url


def _file_content(file_url: str) -> bytes:
	return frappe.get_doc("File", {"file_url": file_url}).get_content()


# --- Admin actions --------------------------------------------------------------------


def _require_admin():
	if not (has_full_access() or "Construction Sales" in frappe.get_roles()):
		frappe.throw(_("Only the office can do this"), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def send_for_signature(
	estimate: str, signer_user: str, contract_template: str | None = None, expires_in_days: int = 14
) -> dict:
	""" "ابعت للتوقيع": render the PDF, store it privately with its hash, create the request, notify."""
	_require_admin()
	est = frappe.get_doc("Estimate", estimate)
	if est.docstatus != 1 or est.status != "Approved":
		frappe.throw(_("Approve the estimate first"))
	if "Construction Client" not in frappe.get_roles(signer_user):
		frappe.throw(_("The signer must be a client with portal access"))
	if contract_template:
		est.db_set("contract_template", contract_template)
	ensure_contract_template()
	pdf = frappe.get_print(
		"Estimate", est.name, print_format=CONTRACT_PRINT_FORMAT, as_pdf=True, no_letterhead=1
	)
	req = frappe.get_doc(
		{
			"doctype": "Signature Request",
			"title": est.title,
			"reference_doctype": "Estimate",
			"reference_name": est.name,
			"contract_template": est.contract_template or DEFAULT_TEMPLATE,
			"customer": est.customer,
			"signer_user": signer_user,
			"status": "Sent",
			"sent_on": now_datetime(),
			"expires_on": add_days(now_datetime(), cint(expires_in_days) or 14),
		}
	)
	_event(req, "Sent")
	req.insert(ignore_permissions=True)
	req.document_pdf = _save_private_file(f"{req.name}.pdf", pdf, req.name, "document_pdf")
	req.pdf_sha256 = sha256(pdf)
	req.flags.allow_system_update = True
	req.save(ignore_permissions=True)
	_notify(signer_user, req, _("مستند مستني توقيعك: {0}").format(est.title))
	mobile = frappe.db.get_value("User", signer_user, "mobile_no") or ""
	link = get_url(f"/portal/sign/{req.name}")
	wa = ""
	if mobile.startswith("01"):
		from urllib.parse import quote

		wa = f"https://wa.me/20{mobile[1:]}?text=" + quote(f"مستند مستني توقيعك: {est.title}\n{link}")
	return {"request": req.name, "link": link, "whatsapp_url": wa}


@frappe.whitelist(methods=["POST"])
def resend(request: str) -> dict:
	"""Unlocks a locked request (or re-sends it); the code is reset."""
	_require_admin()
	req = frappe.get_doc("Signature Request", request)
	if req.status in ("Signed", "Declined"):
		frappe.throw(_("This request is closed"))
	req.status = "Sent"
	req.otp_hash = None
	req.otp_expires_on = None
	req.otp_attempts = 0
	if get_datetime(req.expires_on) <= now_datetime():
		req.expires_on = add_days(now_datetime(), 14)
	_event(req, "Resent")
	req.flags.allow_system_update = True
	req.save(ignore_permissions=True)
	_notify(req.signer_user, req, _("مستند مستني توقيعك: {0}").format(req.title))
	return {"status": req.status}


@frappe.whitelist()
def verify(request: str) -> dict:
	"""Recomputes the hashes of the stored files and compares them with the recorded ones."""
	req = frappe.get_doc("Signature Request", request)
	req.check_permission("read")
	original_ok = sha256(_file_content(req.document_pdf)) == req.pdf_sha256
	signed_ok = None
	if req.signed_pdf:
		signed_ok = sha256(_file_content(req.signed_pdf)) == req.signed_pdf_sha256
	return {"original_ok": original_ok, "signed_ok": signed_ok, "ok": original_ok and signed_ok is not False}


# --- Client actions -------------------------------------------------------------------


def _get_for_signer(request: str):
	req = frappe.get_doc("Signature Request", request)
	if req.signer_user != frappe.session.user:
		frappe.throw(_("Not found"), frappe.PermissionError)
	return req


def _check_open(req):
	if req.status in ("Signed", "Declined", "Expired"):
		frappe.throw(_("هذا المستند مقفول"))
	if req.status == "Locked":
		frappe.throw(_("المحاولات خلصت. كلّم المكتب يبعتلك الكود تاني."))
	if get_datetime(req.expires_on) <= now_datetime():
		frappe.throw(_("المستند انتهت صلاحيته. كلّم المكتب."))


@frappe.whitelist()
def my_signature_requests() -> list[dict]:
	return frappe.get_all(
		"Signature Request",
		filters={"signer_user": frappe.session.user},
		fields=["name", "title", "status", "sent_on", "expires_on", "signed_on", "project"],
		order_by="creation desc",
	)


@frappe.whitelist()
def get_request(request: str) -> dict:
	req = _get_for_signer(request)
	if req.status == "Sent":
		req.status = "Viewed"
		_event(req, "Viewed")
		req.flags.allow_system_update = True
		req.save(ignore_permissions=True)
	return {
		"name": req.name,
		"title": req.title,
		"status": req.status,
		"document_pdf": req.document_pdf,
		"signed_pdf": req.signed_pdf,
		"expires_on": req.expires_on,
		"signed_on": req.signed_on,
		"otp_sent": bool(req.otp_hash),
	}


def _otp_hash(request: str, code: str) -> str:
	key = (frappe.local.conf.get("encryption_key") or frappe.local.site or "").encode()
	return hmac.new(key, f"{request}:{code}".encode(), hashlib.sha256).hexdigest()


@frappe.whitelist(methods=["POST"])
def request_otp(request: str) -> dict:
	"""A 6-digit code by email, valid 10 minutes, stored only as a hash."""
	req = _get_for_signer(request)
	_check_open(req)
	code = f"{secrets.randbelow(10**6):06d}"
	req.otp_hash = _otp_hash(req.name, code)
	req.otp_expires_on = now_datetime() + timedelta(minutes=OTP_MINUTES)
	_event(req, "OTP Sent")
	req.flags.allow_system_update = True
	req.save(ignore_permissions=True)
	_deliver_otp(req, code)
	return {"sent": True, "minutes": OTP_MINUTES}


def _deliver_otp(req, code: str):
	email = frappe.db.get_value("User", req.signer_user, "email")
	if email and not email.endswith("@no-email.invalid"):
		frappe.sendmail(
			recipients=[email],
			subject=_("كود التوقيع: {0}").format(code),
			message=_("كود التوقيع على «{0}» هو <b>{1}</b>. الكود صالح لمدة {2} دقايق.").format(
				req.title, code, OTP_MINUTES
			),
			reference_doctype="Signature Request",
			reference_name=req.name,
			now=False,
		)
	if frappe.conf.get("allow_tests") and frappe.conf.get("cc_test_otp"):
		# CI/test sites only: lets the Playwright test read the code (never on a real site).
		frappe.cache.set_value(f"cc:test-otp:{req.name}", code, expires_in_sec=OTP_MINUTES * 60)


@frappe.whitelist(methods=["POST"])
def sign(request: str, code: str, signature: str) -> dict:
	req = _get_for_signer(request)
	_check_open(req)
	if not req.otp_hash or not req.otp_expires_on or get_datetime(req.otp_expires_on) <= now_datetime():
		frappe.throw(_("اطلب كود جديد"))
	if not hmac.compare_digest(req.otp_hash, _otp_hash(req.name, (code or "").strip())):
		req.otp_attempts = cint(req.otp_attempts) + 1
		_event(req, "OTP Failed")
		if req.otp_attempts >= MAX_ATTEMPTS:
			req.status = "Locked"
			req.otp_hash = None
			_event(req, "Locked")
		req.flags.allow_system_update = True
		req.save(ignore_permissions=True)
		if not frappe.in_test:
			frappe.db.commit()  # keep the failed attempt even though this request errors out
		if req.status == "Locked":
			frappe.throw(_("المحاولات خلصت. كلّم المكتب يبعتلك الكود تاني."), frappe.PermissionError)
		frappe.throw(_("الكود غلط. فاضل {0} محاولة.").format(MAX_ATTEMPTS - req.otp_attempts))
	if not (signature or "").startswith("data:image/png;base64,") or len(signature) > 2_000_000:
		frappe.throw(_("ارسم التوقيع"))

	ip, _ua = _request_info()
	req.signature_image = signature
	req.signed_on = now_datetime()
	req.signed_ip = ip
	req.otp_hash = None
	req.status = "Signed"
	_event(req, "Signed")
	req.flags.allow_system_update = True
	req.save(ignore_permissions=True)

	signed = build_signed_pdf(req)
	req.reload()
	req.signed_pdf = _save_private_file(f"{req.name}-signed.pdf", signed, req.name, "signed_pdf")
	req.signed_pdf_sha256 = sha256(signed)
	req.flags.allow_system_update = True
	req.flags.final_write = True
	req.save(ignore_permissions=True)

	project = kickoff(req) if req.reference_doctype == "Estimate" else None
	_notify_office(req, _("اتوقّع: {0}").format(req.title))
	return {"status": "Signed", "project": project}


@frappe.whitelist(methods=["POST"])
def decline(request: str, reason: str) -> dict:
	req = _get_for_signer(request)
	_check_open(req)
	if not (reason or "").strip():
		frappe.throw(_("اكتب السبب"))
	req.status = "Declined"
	req.decline_reason = reason.strip()[:2000]
	_event(req, "Declined", req.decline_reason)
	req.flags.allow_system_update = True
	req.save(ignore_permissions=True)
	_notify_office(req, _("العميل رفض «{0}»: {1}").format(req.title, req.decline_reason))
	return {"status": "Declined"}


# --- Signed PDF -----------------------------------------------------------------------


def build_signed_pdf(req) -> bytes:
	"""Original pages + a signature page (name, signature image, time, IP, both hashes)."""
	from pypdf import PdfReader, PdfWriter

	original = _file_content(req.document_pdf)
	page = frappe.get_print(
		"Signature Request", req.name, print_format=SIGNATURE_PAGE_FORMAT, as_pdf=True, no_letterhead=1
	)
	writer = PdfWriter()
	for part in (original, page):
		for p in PdfReader(io.BytesIO(part)).pages:
			writer.add_page(p)
	out = io.BytesIO()
	writer.write(out)
	return out.getvalue()


# --- Kickoff --------------------------------------------------------------------------


def _customer_for(est) -> str:
	if est.customer:
		return est.customer
	from erpnext.crm.doctype.lead.lead import make_customer

	existing = frappe.db.get_value("Customer", {"lead_name": est.lead}, "name")
	if existing:
		return existing
	cust = make_customer(est.lead)
	cust.flags.ignore_permissions = True
	cust.insert()
	return cust.name


def kickoff(req) -> str:
	"""A signed contract creates the project, weighted stages, tasks and payment milestones."""
	est = frappe.get_doc("Estimate", req.reference_name)
	if est.project:
		return est.project
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	settings = frappe.get_cached_doc("Inceptiondesign Settings")
	users = [{"user": req.signer_user, "welcome_email_sent": 1}]
	if settings.default_engineer:
		users.append({"user": settings.default_engineer, "welcome_email_sent": 1})
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": est.title,
			"company": company,
			"customer": _customer_for(est),
			"estimated_costing": est.subtotal,
			"users": users,
		}
	)
	project.flags.ignore_permissions = True
	project.insert()

	sections = est.section_totals()
	total = sum(sections.values(), D(0))
	weights = [round2(D(100) * amount / total) if total else D(0) for amount in sections.values()]
	if weights:
		weights[-1] += D(100) - sum(weights, D(0))
	stage_by_section = {}
	for order, (section, weight) in enumerate(zip(sections, weights, strict=True), start=1):
		stage = frappe.get_doc(
			{
				"doctype": "Project Stage",
				"project": project.name,
				"stage_name": section,
				"weight": weight,
				"sort_order": order,
				"progress_mode": "Manual",
			}
		)
		stage.flags.ignore_permissions = True
		stage.insert()
		stage_by_section[section] = stage.name
		task = frappe.get_doc({"doctype": "Task", "subject": section, "project": project.name})
		task.flags.ignore_permissions = True
		task.insert()
	for term, amount in zip(est.payment_terms, term_amounts(est), strict=True):
		m = frappe.get_doc(
			{
				"doctype": "Payment Milestone",
				"project": project.name,
				"project_stage": stage_by_section.get(term.after_section),
				"label": term.label,
				"amount": amount,
				"status": "Upcoming" if term.after_section else "Due",
			}
		)
		m.flags.ignore_permissions = True
		m.insert()
	est.db_set("project", project.name)
	req.db_set("project", project.name)
	return project.name


# --- Notifications and scheduler ------------------------------------------------------


def _notify(user: str, req, subject: str):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	enqueue_create_notification(
		[user],
		{
			"type": "Alert",
			"document_type": "Signature Request",
			"document_name": req.name,
			"subject": subject,
		},
	)


def _notify_office(req, subject: str):
	admins = frappe.get_all(
		"Has Role",
		filters={"role": "Construction Admin", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	for user in admins:
		if user not in ("Administrator", "Guest"):
			_notify(user, req, subject)


def expire_requests():
	"""Daily job: open requests past `expires_on` become Expired."""
	for name in frappe.get_all(
		"Signature Request",
		filters={"status": ["in", ["Sent", "Viewed", "Locked"]], "expires_on": ["<", now_datetime()]},
		pluck="name",
	):
		req = frappe.get_doc("Signature Request", name)
		req.status = "Expired"
		_event(req, "Expired")
		req.flags.allow_system_update = True
		req.save(ignore_permissions=True)
