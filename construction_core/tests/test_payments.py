"""Phase 15: gateway HMAC, webhook idempotency, missed-webhook sweep, manual transfers,
receipts, reminders over 30 days, refunds. The gateway is mocked: no network, no keys in git."""

import io
import json
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from construction_core.api import public
from construction_core.payments import online, paymob, reminders
from construction_core.payments.gateway import Checkout, Transaction
from construction_core.tests.factories import make_milestone, make_project, make_user, stages_of
from construction_core.tests.test_esign import blank_pdf
from construction_core.tests.test_money import make_customer

HMAC_SECRET = "test-hmac-secret-not-real"
ACC_MANAGER = "cc-acc-manager@example.com"
ACC_USER = "cc-acc-user@example.com"


def user_with(email, role):
	if not frappe.db.exists("User", email):
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": role, "send_welcome_email": 0})
		u.insert(ignore_permissions=True)
		u.add_roles(role)
	return email


def callback_obj(reference: str, tx_id: int, cents: int, success=True) -> dict:
	return {
		"amount_cents": cents,
		"created_at": "2026-11-17T10:00:00.000000",
		"currency": "EGP",
		"error_occured": False,
		"has_parent_transaction": False,
		"id": tx_id,
		"integration_id": 4097558,
		"is_3d_secure": True,
		"is_auth": False,
		"is_capture": False,
		"is_refunded": False,
		"is_standalone_payment": True,
		"is_voided": False,
		"order": {"id": 900000 + tx_id, "merchant_order_id": reference},
		"owner": 302852,
		"pending": False,
		"source_data": {"pan": "2346", "sub_type": "MasterCard", "type": "card"},
		"success": success,
	}


def post_webhook(obj: dict, signature: str | None):
	body = json.dumps({"type": "TRANSACTION", "obj": obj})
	env = EnvironBuilder(
		method="POST",
		path="/api/method/construction_core.api.public.paymob_webhook",
		query_string={"hmac": signature} if signature else None,
		data=body,
		content_type="application/json",
	).get_environ()
	frappe.local.request = Request(env)
	frappe.local.request_ip = "127.0.0.1"
	frappe.local.response = frappe._dict()
	user = frappe.session.user
	frappe.set_user("Guest")
	try:
		return public.paymob_webhook(), frappe.local.response.get("http_status_code")
	finally:
		frappe.set_user(user)


class TestPaymob(IntegrationTestCase):
	def test_hmac_string_matches_paymob_example(self):
		# The example from developers.paymob.com (HMAC Transaction Callback)
		obj = {
			"amount_cents": 100000,
			"created_at": "2024-06-13T11:33:44.592345",
			"currency": "EGP",
			"error_occured": False,
			"has_parent_transaction": False,
			"id": 192036465,
			"integration_id": 4097558,
			"is_3d_secure": True,
			"is_auth": False,
			"is_capture": False,
			"is_refunded": False,
			"is_standalone_payment": True,
			"is_voided": False,
			"order": {"id": 217503754},
			"owner": 302852,
			"pending": False,
			"source_data": {"pan": "2346", "sub_type": "MasterCard", "type": "card"},
			"success": True,
		}
		self.assertEqual(
			paymob.hmac_string(obj),
			"1000002024-06-13T11:33:44.592345EGPfalsefalse1920364654097558truefalsefalsefalsetruefalse217503754302852false2346MasterCardcardtrue",
		)


class TestOnlinePayments(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.client = make_user("client1")
		cls.eng = make_user("eng1")
		cls.project = make_project("مشروع الدفع أونلاين", [cls.client, cls.eng])
		frappe.db.set_value("Project", cls.project, "customer", make_customer("عميل الدفع أونلاين"))
		s = frappe.get_doc("Inceptiondesign Settings")
		s.enable_online_payments = 1
		s.gateway_mode = "Test"
		s.paymob_public_key = "pk_test_x"
		s.paymob_secret_key = "sk_test_x"
		s.paymob_hmac_secret = HMAC_SECRET
		s.paymob_api_key = "api_test_x"
		s.paymob_card_integration_id = 111
		s.paymob_wallet_integration_id = 222
		s.save(ignore_permissions=True)
		user_with(ACC_MANAGER, "Accounts Manager")
		user_with(ACC_USER, "Accounts User")

	def setUp(self):
		frappe.clear_document_cache("Inceptiondesign Settings")
		p1 = patch.object(
			paymob.Paymob, "create_checkout", return_value=Checkout("https://pay.test/x", "ORD-1")
		)
		p2 = patch("frappe.get_print", side_effect=blank_pdf)
		self.addCleanup(p1.stop)
		self.addCleanup(p2.stop)
		p1.start()
		p2.start()

	def due_milestone(self, amount=10000, label="دفعة الأونلاين"):
		m = make_milestone(self.project, stages_of(self.project)[0], amount, label)
		frappe.db.set_value("Payment Milestone", m, "status", "Due")
		return m

	def checkout(self, milestone):
		with self.set_user(self.client):
			res = online.start_checkout(milestone, "Card")
		return frappe.get_doc("Online Payment", res["payment"])

	def test_pay_due_milestone_by_webhook_once(self):
		m = self.due_milestone()
		p = self.checkout(m)
		self.assertEqual((p.status, p.amount, p.checkout_url), ("Pending", 10000, "https://pay.test/x"))
		obj = callback_obj(p.reference, 501, 1000000)
		res, _code = post_webhook(obj, paymob.sign(obj, HMAC_SECRET))
		self.assertEqual(res, {"ok": True})
		p.reload()
		self.assertEqual(p.status, "Paid")
		pe = frappe.get_doc("Payment Entry", p.payment_entry)
		self.assertEqual((pe.docstatus, pe.paid_amount, pe.reference_no), (1, 10000, "501"))
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Paid")
		self.assertEqual(frappe.db.get_value("Sales Invoice", p.sales_invoice, "docstatus"), 1)
		# the same webhook again: still one Payment Entry
		post_webhook(obj, paymob.sign(obj, HMAC_SECRET))
		self.assertEqual(frappe.db.count("Payment Entry", {"reference_no": "501", "docstatus": 1}), 1)
		# the client can download the receipt
		with self.set_user(self.client):
			resp = online.receipt_pdf(p.name)
		self.assertEqual(resp.content_type, "application/pdf")

	def test_bad_signature_rejected_and_logged(self):
		m = self.due_milestone(label="دفعة التوقيع الغلط")
		p = self.checkout(m)
		obj = callback_obj(p.reference, 502, 1000000)
		before = frappe.db.count("Error Log", {"method": ["like", "%bad signature%"]})
		res, code = post_webhook(obj, "0" * 128)
		self.assertEqual((res, code), ({"ok": False}, 401))
		res, code = post_webhook(obj, None)
		self.assertEqual(code, 401)
		tampered = dict(obj, amount_cents=1)
		res, code = post_webhook(tampered, paymob.sign(obj, HMAC_SECRET))
		self.assertEqual(code, 401)
		self.assertEqual(frappe.db.count("Error Log", {"method": ["like", "%bad signature%"]}), before + 3)
		self.assertEqual(frappe.db.get_value("Online Payment", p.name, "status"), "Pending")
		self.assertFalse(frappe.db.exists("Payment Entry", {"reference_no": "502"}))

	def test_sweep_reconciles_missed_webhook(self):
		m = self.due_milestone(label="دفعة الويب هوك الضايع")
		p = self.checkout(m)
		frappe.db.set_value("Online Payment", p.name, "creation", add_days(p.creation, -1))
		tx = Transaction("503", p.reference, True, False, Decimal("10000"))
		with patch.object(paymob.Paymob, "inquire", return_value=tx) as inquire:
			online.sweep_pending()
		self.assertTrue(inquire.called)
		p.reload()
		self.assertEqual(p.status, "Paid")
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Paid")

	def test_failed_payment_does_not_book(self):
		m = self.due_milestone(label="دفعة فاشلة")
		p = self.checkout(m)
		obj = callback_obj(p.reference, 504, 1000000, success=False)
		post_webhook(obj, paymob.sign(obj, HMAC_SECRET))
		self.assertEqual(frappe.db.get_value("Online Payment", p.name, "status"), "Failed")
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Due")

	def test_manual_transfer_confirmed_by_accountant(self):
		m = self.due_milestone(label="دفعة التحويل")
		frappe.set_user(self.client)
		f = frappe.get_doc(
			{"doctype": "File", "file_name": "transfer.jpg", "content": b"\xff\xd8receipt", "is_private": 1}
		).insert(ignore_permissions=True)
		frappe.set_user("Administrator")
		with self.set_user(self.client):
			res = online.submit_transfer(m, "InstaPay", f.file_url, "حولت من البنك الأهلي")
		self.assertEqual(res["status"], "Awaiting Confirmation")
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": ACC_USER, "document_name": res["payment"]})
		)
		with self.set_user(self.eng):
			self.assertRaises(frappe.PermissionError, online.confirm_transfer, res["payment"])
		with self.set_user(ACC_USER):
			pe = online.confirm_transfer(res["payment"])
		self.assertEqual(frappe.db.get_value("Payment Entry", pe, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Paid")

	def test_refund_only_accounts_manager(self):
		m = self.due_milestone(label="دفعة الاسترداد")
		p = self.checkout(m)
		obj = callback_obj(p.reference, 505, 1000000)
		post_webhook(obj, paymob.sign(obj, HMAC_SECRET))
		p.reload()
		with self.set_user(ACC_USER):
			self.assertRaises(frappe.PermissionError, online.refund, p.name, "غلط")
		with (
			patch.object(paymob.Paymob, "refund", return_value="RF-1") as gw_refund,
			self.set_user(ACC_MANAGER),
		):
			res = online.refund(p.name, "العميل دفع مرتين")
		gw_refund.assert_called_once()
		self.assertEqual(frappe.db.get_value("Payment Entry", res["payment_entry"], "docstatus"), 2)
		p.reload()
		self.assertEqual((p.status, p.refund_reference, p.refunded_by), ("Refunded", "RF-1", ACC_MANAGER))
		self.assertEqual(frappe.db.get_value("Payment Milestone", m, "status"), "Invoiced")

	def test_live_keys_refused_on_test_site(self):
		frappe.db.set_single_value("Inceptiondesign Settings", "gateway_mode", "Live")
		frappe.clear_document_cache("Inceptiondesign Settings")
		try:
			m = self.due_milestone(label="دفعة لايف")
			with self.set_user(self.client):
				self.assertRaises(frappe.ValidationError, online.start_checkout, m, "Card")
		finally:
			frappe.db.set_single_value("Inceptiondesign Settings", "gateway_mode", "Test")
			frappe.clear_document_cache("Inceptiondesign Settings")

	def test_other_client_cannot_pay(self):
		m = self.due_milestone(label="دفعة مش ليك")
		with self.set_user(make_user("client2")):
			self.assertRaises(frappe.PermissionError, online.start_checkout, m, "Card")


class TestReminders(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.client = make_user("client1")
		cls.project = make_project("مشروع التذكير", [cls.client])

	def test_thirty_days_exactly_four_reminders(self):
		start = getdate("2027-03-01")
		due = add_days(start, 9)  # "day 10"
		m = make_milestone(self.project, None, 5000, "دفعة التذكير")
		frappe.db.set_value("Payment Milestone", m, {"status": "Due", "due_date": due})
		days = []
		for day in range(1, 31):
			today = add_days(start, day - 1)
			sent = reminders.send_due_reminders(today)
			for name in sent:
				if frappe.db.get_value("Payment Reminder Log", name, "payment_milestone") == m:
					days.append(day)
			if day == 10:
				reminders.send_due_reminders(today)  # a second run the same day sends nothing new
		self.assertEqual(days, [7, 10, 17, 24])
		logs = frappe.get_all(
			"Payment Reminder Log",
			filters={"payment_milestone": m},
			fields=["offset_days", "recipient", "channels"],
		)
		self.assertEqual(sorted(l.offset_days for l in logs), [-3, 0, 7, 14])
		self.assertTrue(all(l.recipient == self.client and "portal" in l.channels for l in logs))
		# paid milestones get nothing
		frappe.db.set_value("Payment Milestone", m, "status", "Paid")
		frappe.db.delete("Payment Reminder Log", {"payment_milestone": m})
		self.assertFalse(
			[
				n
				for n in reminders.send_due_reminders(add_days(start, 6))
				if frappe.db.get_value("Payment Reminder Log", n, "payment_milestone") == m
			]
		)
