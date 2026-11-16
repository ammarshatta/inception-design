"""Admin actions on the Project form (phase 2, task 3). Construction Admin / System Manager only."""

import re
import secrets
import string
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, get_url
from frappe.utils.password import update_password

from construction_core.branding import get_branding
from construction_core.permissions import CLIENT_ROLE, ENGINEER_ROLE, has_full_access
from construction_core.sharing import hash_token, new_token, share_url

EGYPT_MOBILE_RE = re.compile(r"^01[0125][0-9]{8}$")
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,29}$")
TEMP_PASSWORD_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0OolI1")
NO_EMAIL_DOMAIN = "no-email.invalid"  # RFC 2606: never deliverable


def _require_admin():
	if not has_full_access():
		frappe.throw(_("Only the office admin can do this"), frappe.PermissionError)


def _get_project(project: str):
	_require_admin()
	if not frappe.db.exists("Project", project):
		frappe.throw(_("Project not found"), frappe.DoesNotExistError)
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	return doc


def temp_password(length: int = 12) -> str:
	while True:
		pwd = "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _i in range(length))
		if any(c.isdigit() for c in pwd) and any(c.isupper() for c in pwd) and any(c.islower() for c in pwd):
			return pwd


def normalize_mobile(mobile: str | None) -> str:
	mobile = re.sub(r"[\s-]", "", cstr(mobile))
	if mobile.startswith("+20"):
		mobile = "0" + mobile[3:]
	elif mobile.startswith("0020"):
		mobile = "0" + mobile[4:]
	return mobile


# --- Stages ---------------------------------------------------------------------------


@frappe.whitelist()
def get_project_stages(project: str) -> dict:
	_get_project(project)
	stages = frappe.get_all(
		"Project Stage",
		filters={"project": project},
		fields=[
			"name",
			"stage_name",
			"weight",
			"progress",
			"status",
			"planned_start",
			"planned_end",
			"sort_order",
		],
		order_by="sort_order asc, creation asc",
	)
	total = flt(sum(flt(s.weight) for s in stages), 2)
	return {"stages": stages, "total_weight": total, "ok": not stages or total == 100}


@frappe.whitelist(methods=["POST"])
def move_stage(stage: str, direction: str) -> dict:
	"""Swap a stage with its neighbour. direction: 'up' or 'down'."""
	project = frappe.db.get_value("Project Stage", stage, "project")
	_get_project(project)
	names = frappe.get_all(
		"Project Stage", filters={"project": project}, order_by="sort_order asc, creation asc", pluck="name"
	)
	i = names.index(stage)
	j = i - 1 if direction == "up" else i + 1
	if 0 <= j < len(names):
		names[i], names[j] = names[j], names[i]
	for order, name in enumerate(names, start=1):
		frappe.db.set_value("Project Stage", name, "sort_order", order, update_modified=False)
	return get_project_stages(project)


# --- Team -----------------------------------------------------------------------------


def _add_project_user(project_doc, user: str):
	if not any(row.user == user for row in project_doc.users):
		# We send our own welcome (Frappe's set-password email or the WhatsApp message),
		# so ERPNext's project welcome email is marked as sent.
		project_doc.append("users", {"user": user, "welcome_email_sent": 1})


@frappe.whitelist(methods=["POST"])
def add_engineer(project: str, user: str) -> dict:
	doc = _get_project(project)
	if ENGINEER_ROLE not in frappe.get_roles(user):
		frappe.throw(_("This user is not an engineer"))
	_add_project_user(doc, user)
	doc.save()
	return {"user": user, "team": [r.user for r in doc.users]}


@frappe.whitelist(methods=["POST"])
def add_client(
	project: str, full_name: str, mobile: str, email: str | None = None, username: str | None = None
) -> dict:
	"""Create or link Customer + Contact + portal User and add them to the project (one transaction)."""
	doc = _get_project(project)
	full_name = cstr(full_name).strip()
	mobile = normalize_mobile(mobile)
	email = cstr(email).strip().lower() or None
	username = cstr(username).strip().lower() or None

	if not full_name:
		frappe.throw(_("Name is required"))
	if not EGYPT_MOBILE_RE.match(mobile):
		frappe.throw(_("Mobile number must be an Egyptian mobile like 01xxxxxxxxx"))
	if email:
		from frappe.utils import validate_email_address

		validate_email_address(email, throw=True)
	else:
		if not username:
			frappe.throw(_("Username is required when there is no email"))
		if not USERNAME_RE.match(username):
			frappe.throw(_("Username: 3–30 English lowercase letters, digits, dot, dash or underscore"))

	user_name, created = _get_or_create_user(full_name, mobile, email, username)
	customer = _get_or_create_customer(full_name, doc)
	_get_or_create_contact(full_name, mobile, email, user_name, customer)

	_add_project_user(doc, user_name)
	if not doc.customer:
		doc.customer = customer
	doc.save()

	result = {"user": user_name, "customer": customer, "created": created, "login_url": get_url("/login")}
	if not email:
		pwd = temp_password()
		update_password(user_name, pwd)
		frappe.db.set_value("User", user_name, "must_change_password", 1)
		login_name = frappe.db.get_value("User", user_name, "username") or user_name
		result.update(
			{
				"username": login_name,
				"temp_password": pwd,  # shown once in the dialog; never stored or logged
				"whatsapp_url": whatsapp_url(mobile, full_name, login_name, pwd),
			}
		)
	return result


def _get_or_create_user(full_name, mobile, email, username) -> tuple[str, bool]:
	if email and frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		created = False
	elif username and frappe.db.exists("User", {"username": username}):
		frappe.throw(_("Username {0} is already taken").format(username))
	else:
		first, _sep, last = full_name.partition(" ")
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email or f"{username}@{NO_EMAIL_DOMAIN}",
				"username": username,
				"first_name": first,
				"last_name": last,
				"mobile_no": mobile,
				"user_type": "Website User",
				"send_welcome_email": 1 if email else 0,
				"language": "ar",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
		created = True
	if CLIENT_ROLE not in frappe.get_roles(user.name):
		user.flags.ignore_permissions = True
		user.add_roles(CLIENT_ROLE)
	return user.name, created


def _get_or_create_customer(full_name: str, project_doc) -> str:
	if project_doc.customer:
		return project_doc.customer
	existing = frappe.db.get_value("Customer", {"customer_name": full_name}, "name")
	if existing:
		return existing
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": full_name,
			"customer_type": "Individual",
			"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group")
			or frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
			or frappe.db.get_value("Customer Group", {}, "name"),
			"territory": frappe.db.get_single_value("Selling Settings", "territory")
			or frappe.db.get_value("Territory", {"is_group": 0}, "name")
			or frappe.db.get_value("Territory", {}, "name"),
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()
	return customer.name


def _get_or_create_contact(full_name, mobile, email, user, customer) -> str:
	existing = frappe.db.get_value("Contact", {"user": user}, "name")
	if existing:
		contact = frappe.get_doc("Contact", existing)
	else:
		first, _sep, last = full_name.partition(" ")
		contact = frappe.get_doc({"doctype": "Contact", "first_name": first, "last_name": last, "user": user})
		contact.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
		if email:
			contact.append("email_ids", {"email_id": email, "is_primary": 1})
	if not any(link.link_doctype == "Customer" and link.link_name == customer for link in contact.links):
		contact.append("links", {"link_doctype": "Customer", "link_name": customer})
	contact.flags.ignore_permissions = True
	contact.save()
	return contact.name


def whatsapp_url(mobile: str, full_name: str, username: str, password: str) -> str:
	office = get_branding()["office_name"]
	text = "\n".join(
		[
			f"أهلاً {full_name}،",
			f"حسابك على بوابة متابعة مشروعك مع {office} جاهز."
			if office
			else "حسابك على بوابة متابعة مشروعك جاهز.",
			f"الدخول: {get_url('/login')}",
			f"اسم المستخدم: {username}",
			f"كلمة السر المؤقتة: {password}",
			"أول ما تدخل هيطلب منك تغيّر كلمة السر.",
		]
	)
	return f"https://wa.me/20{mobile[1:]}?text={quote(text)}"


# --- Publishing -----------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def new_share_link(project: str) -> dict:
	"""New secret link; the old one stops working. The full link is returned once."""
	doc = _get_project(project)
	token = new_token()
	doc.share_token_hash = hash_token(token)
	if doc.visibility == "private":
		doc.visibility = "link"
	doc.save()
	return {"url": share_url(doc.name, token), "visibility": doc.visibility}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def engineer_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link search for the Add Engineer dialog: enabled users with the engineer role."""
	_require_admin()
	has_role = frappe.qb.DocType("Has Role")
	user = frappe.qb.DocType("User")
	return (
		frappe.qb.from_(user)
		.join(has_role)
		.on((has_role.parent == user.name) & (has_role.parenttype == "User"))
		.select(user.name, user.full_name)
		.where((has_role.role == ENGINEER_ROLE) & (user.enabled == 1))
		.where((user.name.like(f"%{txt}%")) | (user.full_name.like(f"%{txt}%")))
		.distinct()
		.limit(page_len)
		.offset(start)
		.run()
	)
