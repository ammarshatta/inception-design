"""Test data factory (phase 1, task 6). Used only by tests; never installed by fixtures.

Creates an admin, 2 engineers, 2 clients, a "تشطيب شقة" template with 8 stages,
and 2 projects. Every function is idempotent so tests can call it repeatedly.
"""

import frappe

TEMPLATE_NAME = "تشطيب شقة (اختبار)"

# (stage, weight, checklist lines) — weights add up to 100
TEMPLATE_STAGES = [
	("تكسير ونقل مخلفات", 5, "تكسير الحوائط\nنقل المخلفات"),
	("تأسيس سباكة", 10, "مواسير التغذية\nمواسير الصرف\nاختبار الضغط"),
	("تأسيس كهرباء", 12, "خراطيم\nعلب\nسحب السلك\nالطبلون"),
	("محارة", 15, "بؤج وأوتار\nطرطشة\nبطانة\nضهارة"),
	("أرضيات وسيراميك", 20, "تسوية\nتركيب\nترويب"),
	("نجارة وألوميتال", 15, "أبواب\nشبابيك"),
	("دهانات", 15, "معجون\nسيلر\nوشين نهائي"),
	("تشطيب نهائي وتسليم", 8, "تنظيف\nاستلام العميل"),
]

USERS = {
	"admin": ("cc-admin@example.com", "أدمن", "الاختبار", "Construction Admin"),
	"eng1": ("cc-eng1@example.com", "كريم", "المهندس", "Construction Engineer"),
	"eng2": ("cc-eng2@example.com", "سامح", "المهندس", "Construction Engineer"),
	"client1": ("cc-client1@example.com", "أحمد", "العميل", "Construction Client"),
	"client2": ("cc-client2@example.com", "منى", "العميلة", "Construction Client"),
}


def make_user(key: str) -> str:
	email, first, last, role = USERS[key]
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first,
				"last_name": last,
				"send_welcome_email": 0,
				"user_type": "System User" if role != "Construction Client" else "Website User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
	user = frappe.get_doc("User", email)
	if role not in [r.role for r in user.roles]:
		user.flags.ignore_permissions = True
		user.add_roles(role)
	return email


def make_template() -> str:
	if not frappe.db.exists("Phase Template", TEMPLATE_NAME):
		frappe.get_doc(
			{
				"doctype": "Phase Template",
				"template_name": TEMPLATE_NAME,
				"stages": [
					{"stage_name": name, "weight": weight, "checklist_text": checklist}
					for name, weight, checklist in TEMPLATE_STAGES
				],
			}
		).insert(ignore_permissions=True)
	return TEMPLATE_NAME


def get_company() -> str:
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	if not company:
		raise RuntimeError("No Company found. Run the setup wizard (before_tests does this in CI).")
	return company


def make_project(title: str, members: list[str], with_template: bool = True) -> str:
	existing = frappe.db.get_value("Project", {"project_name": title}, "name")
	if existing:
		return existing
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": title,
			"company": get_company(),
			"phase_template": make_template() if with_template else None,
			# welcome_email_sent=1: ERPNext emails new project users on validate,
			# and test sites have no outgoing email account.
			"users": [{"user": u, "welcome_email_sent": 1} for u in members],
		}
	)
	project.insert(ignore_permissions=True)
	return project.name


def make_world() -> frappe._dict:
	"""The full data set: users, template, and two projects with separate teams."""
	users = frappe._dict({key: make_user(key) for key in USERS})
	template = make_template()
	p1 = make_project("مشروع اختبار 1", [users.eng1, users.client1])
	p2 = make_project("مشروع اختبار 2", [users.eng2, users.client2])
	return frappe._dict(users=users, template=template, p1=p1, p2=p2)


def stages_of(project: str) -> list[str]:
	return frappe.get_all(
		"Project Stage",
		filters={"project": project},
		order_by="sort_order asc",
		pluck="name",
		ignore_permissions=True,
	)


def make_update(project: str, stage: str, internal_only: int = 0, text: str = "تحديث") -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Stage Update",
			"project": project,
			"project_stage": stage,
			"text": text,
			"internal_only": internal_only,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def make_milestone(project: str, stage: str | None, amount: float = 1000, label: str = "دفعة") -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Payment Milestone",
			"project": project,
			"project_stage": stage,
			"label": label,
			"amount": amount,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def make_message(project: str, kind: str = "Text", **kw) -> str:
	doc = frappe.get_doc({"doctype": "Project Message", "project": project, "kind": kind, **kw})
	doc.insert(ignore_permissions=True)
	return doc.name
