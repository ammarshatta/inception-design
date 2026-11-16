"""Creates the user for the Playwright portal test (CI and local). Test sites only."""

import frappe
from frappe.utils.password import update_password


def create_e2e_user(email: str, password: str, first_name: str = "عميل", last_name: str = "التجربة"):
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		user.add_roles("Construction Client")
	update_password(email, password)
	frappe.db.commit()
	return frappe.db.get_value("User", email, "full_name")


def create_temp_password_client(username: str = "e2e.temp") -> dict:
	"""A project plus a client added without email (temporary password), for Playwright."""
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	from construction_core.api.admin import add_client
	from construction_core.tests.factories import make_project

	existing = frappe.db.get_value("User", {"username": username}, "name")
	if existing:
		frappe.delete_doc("User", existing, ignore_permissions=True, force=True)
	project = make_project("مشروع تجربة كلمة السر المؤقتة", [])
	res = add_client(project, "عميل مؤقت", "01098765432", username=username)
	frappe.db.commit()
	return {"username": res["username"], "password": res["temp_password"]}


def create_engineer_project(email: str, password: str) -> dict:
	"""An engineer with a password and a project from the test template, for Playwright."""
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	from construction_core.api.admin import add_engineer
	from construction_core.tests.factories import make_project

	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "مهندس",
				"last_name": "التجربة",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		user.add_roles("Construction Engineer")
	update_password(email, password)
	project = make_project("مشروع تجربة المهندس", [])
	add_engineer(project, email)
	frappe.db.commit()
	return {"project": project}


def add_chat_client(project: str, email: str, password: str) -> dict:
	"""A client with a password on the given project, for the two-browser chat test."""
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "عميل",
				"last_name": "الشات",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		user.add_roles("Construction Client")
	update_password(email, password)
	doc = frappe.get_doc("Project", project)
	if email not in [r.user for r in doc.users]:
		doc.append("users", {"user": email, "welcome_email_sent": 1})
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"project": project}


def make_invoice_pdf(project: str, path: str) -> dict:
	"""Submits a Sales Invoice for a milestone of the project and writes its Arabic PDF to `path`."""
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	from construction_core.api.portal import INVOICE_PRINT_FORMAT
	from construction_core.tests.factories import make_milestone, stages_of

	company = frappe.db.get_value("Project", project, "company")
	item = "خدمات تشطيب"
	if not frappe.db.exists("Item", item):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)
	customer = frappe.db.get_value("Project", project, "customer")
	if not customer:
		customer = (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "أحمد محمود",
					"customer_type": "Individual",
					"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
					"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("Project", project, "customer", customer)
	milestone = make_milestone(project, stages_of(project)[0], 85000, "دفعة بعد التأسيس")
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": company,
			"customer": customer,
			"project": project,
			"items": [{"item_code": item, "qty": 1, "rate": 85000, "description": "دفعة بعد التأسيس"}],
		}
	)
	si.insert(ignore_permissions=True)
	si.submit()
	frappe.db.set_value("Payment Milestone", milestone, {"sales_invoice": si.name, "status": "Invoiced"})
	pdf = frappe.get_print(
		"Sales Invoice", si.name, print_format=INVOICE_PRINT_FORMAT, as_pdf=True, no_letterhead=1
	)
	with open(path, "wb") as f:
		f.write(pdf)
	frappe.db.commit()
	return {"invoice": si.name, "milestone": milestone, "bytes": len(pdf)}


def prepare_signature(email: str, password: str) -> dict:
	"""A client without a project and an approved estimate sent to them for signature."""
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Only on test sites (allow_tests is off)")
	from construction_core.esign import send_for_signature
	from construction_core.tests.test_money import make_customer

	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "عميل",
				"last_name": "التوقيع",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		user.add_roles("Construction Client")
	update_password(email, password)
	est = frappe.get_doc(
		{
			"doctype": "Estimate",
			"title": "عقد تشطيب شقة المعادي",
			"customer": make_customer("عميل التوقيع"),
			"estimate_date": frappe.utils.nowdate(),
			"overhead_pct": 10,
			"profit_pct": 15,
			"lines": [
				{
					"section": "تأسيس سباكة وكهرباء",
					"line_type": "Other",
					"description": "تأسيس",
					"qty": 1,
					"unit_cost": 60000,
				},
				{
					"section": "محارة ودهانات",
					"line_type": "Other",
					"description": "محارة",
					"qty": 150,
					"unit_cost": 400,
				},
			],
			"payment_terms": [
				{"label": "دفعة التعاقد", "percent": 30},
				{"label": "بعد التأسيس", "percent": 40, "after_section": "تأسيس سباكة وكهرباء"},
				{"label": "عند التسليم", "percent": 30, "after_section": "محارة ودهانات"},
			],
		}
	).insert(ignore_permissions=True)
	est.submit()
	res = send_for_signature(est.name, email)
	frappe.db.commit()
	return {"request": res["request"]}


@frappe.whitelist()
def peek_otp(request: str) -> str:
	"""Test sites only (allow_tests + cc_test_otp), Administrator only: the last OTP sent."""
	if not (frappe.conf.get("allow_tests") and frappe.conf.get("cc_test_otp")):
		frappe.throw("Not available", frappe.PermissionError)
	if frappe.session.user != "Administrator":
		frappe.throw("Not available", frappe.PermissionError)
	return frappe.cache.get_value(f"cc:test-otp:{request}")


def signed_pdf_path(request: str) -> str:
	return frappe.get_doc(
		"File", {"file_url": frappe.db.get_value("Signature Request", request, "signed_pdf")}
	).get_full_path()
