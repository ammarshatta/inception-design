"""Phase 8: e-signature, freezing, verification, lockout, kickoff, decline, expiry.

PDF rendering is mocked here (no web server in unit tests); the real Arabic PDF is
rendered in the Playwright run.
"""

import io
from datetime import timedelta
from unittest.mock import patch

import frappe
import frappe.client
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime
from pypdf import PdfReader, PdfWriter

from construction_core import esign
from construction_core.tests.factories import make_user
from construction_core.tests.test_money import make_customer

SIG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def blank_pdf(*args, **kwargs) -> bytes:
	w = PdfWriter()
	w.add_blank_page(width=595, height=842)
	out = io.BytesIO()
	w.write(out)
	return out.getvalue()


class TestESign(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.client = make_user("client1")
		esign.ensure_contract_template()

	def approved_estimate(self, title="عقد تجربة"):
		est = frappe.get_doc(
			{
				"doctype": "Estimate",
				"title": title,
				"customer": make_customer("عميل العقد"),
				"estimate_date": frappe.utils.nowdate(),
				"overhead_pct": 0,
				"profit_pct": 0,
				"lines": [
					{
						"section": "تأسيس",
						"line_type": "Other",
						"description": "تأسيس",
						"qty": 1,
						"unit_cost": 30000,
					},
					{
						"section": "تشطيب",
						"line_type": "Other",
						"description": "تشطيب",
						"qty": 1,
						"unit_cost": 70000,
					},
				],
				"payment_terms": [
					{"label": "دفعة التعاقد", "percent": 30},
					{"label": "بعد التأسيس", "percent": 40, "after_section": "تأسيس"},
					{"label": "عند التسليم", "percent": 30, "after_section": "تشطيب"},
				],
			}
		).insert(ignore_permissions=True)
		est.submit()
		return est

	def send(self, est):
		with patch("frappe.get_print", side_effect=blank_pdf):
			return esign.send_for_signature(est.name, self.client)["request"]

	def otp(self, request) -> str:
		captured = {}
		with patch.object(
			esign, "_deliver_otp", side_effect=lambda req, code: captured.setdefault("code", code)
		):
			with self.set_user(self.client):
				esign.request_otp(request)
		return captured["code"]

	def test_full_signing_and_kickoff(self):
		est = self.approved_estimate()
		request = self.send(est)
		req = frappe.get_doc("Signature Request", request)
		self.assertTrue(req.document_pdf.startswith("/private/"))
		self.assertEqual(esign.sha256(esign._file_content(req.document_pdf)), req.pdf_sha256)

		code = self.otp(request)
		self.assertEqual(len(code), 6)
		self.assertNotIn(code, frappe.db.get_value("Signature Request", request, "otp_hash"))
		with self.set_user(self.client), patch("frappe.get_print", side_effect=blank_pdf):
			esign.get_request(request)
			res = esign.sign(request, code, SIG)
		self.assertEqual(res["status"], "Signed")
		req.reload()
		self.assertEqual(req.status, "Signed")
		self.assertEqual(len(PdfReader(io.BytesIO(esign._file_content(req.signed_pdf))).pages), 2)
		self.assertEqual(esign.sha256(esign._file_content(req.signed_pdf)), req.signed_pdf_sha256)
		events = [e.event for e in req.events]
		for e in ("Sent", "Viewed", "OTP Sent", "Signed"):
			self.assertIn(e, events)

		project = res["project"]
		self.assertTrue(project)
		stages = frappe.get_all(
			"Project Stage",
			filters={"project": project},
			fields=["stage_name", "weight"],
			order_by="sort_order",
		)
		self.assertEqual([(s.stage_name, s.weight) for s in stages], [("تأسيس", 30), ("تشطيب", 70)])
		self.assertEqual(frappe.db.count("Task", {"project": project}), 2)
		milestones = frappe.get_all(
			"Payment Milestone",
			filters={"project": project},
			fields=["label", "amount", "status"],
			order_by="creation",
		)
		self.assertEqual([m.amount for m in milestones], [30000, 40000, 30000])
		self.assertEqual(milestones[0].status, "Due")
		self.assertIn(self.client, [u.user for u in frappe.get_doc("Project", project).users])

	def test_signed_is_frozen_and_tamper_detected(self):
		est = self.approved_estimate("عقد التجميد")
		request = self.send(est)
		code = self.otp(request)
		with self.set_user(self.client), patch("frappe.get_print", side_effect=blank_pdf):
			esign.sign(request, code, SIG)
		req = frappe.get_doc("Signature Request", request)
		req.title = "تعديل"
		self.assertRaises(frappe.PermissionError, req.save)
		req.reload()
		req.flags.allow_system_update = True
		req.decline_reason = "x"
		self.assertRaises(frappe.PermissionError, req.save)
		self.assertRaises(frappe.PermissionError, frappe.delete_doc, "Signature Request", request)
		file_name = frappe.db.get_value("File", {"file_url": req.document_pdf}, "name")
		self.assertRaises(frappe.PermissionError, frappe.delete_doc, "File", file_name)

		self.assertTrue(esign.verify(request)["ok"])
		path = frappe.get_doc("File", file_name).get_full_path()
		with open(path, "ab") as f:
			f.write(b"tampered")
		result = esign.verify(request)
		self.assertFalse(result["original_ok"])
		self.assertFalse(result["ok"])

	def test_fourth_wrong_code_locks_until_resend(self):
		est = self.approved_estimate("عقد القفل")
		request = self.send(est)
		self.otp(request)
		with self.set_user(self.client):
			self.assertRaises(frappe.ValidationError, esign.sign, request, "000000", SIG)
			self.assertRaises(frappe.ValidationError, esign.sign, request, "000001", SIG)
			self.assertRaises(frappe.PermissionError, esign.sign, request, "000002", SIG)
		self.assertEqual(frappe.db.get_value("Signature Request", request, "status"), "Locked")
		with self.set_user(self.client):
			# the 4th try, even with any code, is refused while locked
			self.assertRaises(frappe.ValidationError, esign.sign, request, "123456", SIG)
			self.assertRaises(frappe.ValidationError, esign.request_otp, request)
		esign.resend(request)
		self.assertEqual(frappe.db.get_value("Signature Request", request, "status"), "Sent")
		code = self.otp(request)
		with self.set_user(self.client), patch("frappe.get_print", side_effect=blank_pdf):
			self.assertEqual(esign.sign(request, code, SIG)["status"], "Signed")

	def test_other_client_cannot_see_or_sign(self):
		est = self.approved_estimate("عقد خاص")
		request = self.send(est)
		other = make_user("client2")
		with self.set_user(other):
			self.assertRaises(frappe.PermissionError, esign.get_request, request)
			self.assertNotIn(request, frappe.get_list("Signature Request", pluck="name"))
			self.assertRaises(frappe.PermissionError, frappe.client.get, "Signature Request", request)

	def test_decline_and_expiry(self):
		est = self.approved_estimate("عقد الرفض")
		request = self.send(est)
		with self.set_user(self.client):
			esign.decline(request, "السعر عالي")
		req = frappe.get_doc("Signature Request", request)
		self.assertEqual(req.status, "Declined")
		self.assertEqual(req.decline_reason, "السعر عالي")

		est2 = self.approved_estimate("عقد منتهي")
		request2 = self.send(est2)
		frappe.db.set_value("Signature Request", request2, "expires_on", now_datetime() - timedelta(hours=1))
		esign.expire_requests()
		self.assertEqual(frappe.db.get_value("Signature Request", request2, "status"), "Expired")
		with self.set_user(self.client):
			self.assertRaises(frappe.ValidationError, esign.request_otp, request2)
