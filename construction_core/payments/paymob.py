"""Paymob adapter (cards and Egyptian mobile wallets), Intention API + Unified Checkout.

Endpoints and the HMAC field list follow developers.paymob.com (checked 17 Nov 2026):
- create:   POST {base}/v1/intention/            Authorization: Token <secret key>
- checkout: {base}/unifiedcheckout/?publicKey=<public key>&clientSecret=<client_secret>
- inquiry:  POST {base}/api/ecommerce/orders/transaction_inquiry   (Bearer auth token from API key)
- refund:   POST {base}/api/acceptance/void_refund/refund           Authorization: Token <secret key>
- webhook:  "transaction processed" callback; HMAC-SHA512 over 20 fields of `obj`, in a fixed order,
            with the HMAC secret; the hmac arrives as a query parameter.
"""

import hashlib
import hmac as hmac_lib
from decimal import Decimal
from urllib.parse import urlencode

import frappe
import requests
from frappe import _
from frappe.utils import get_url

from construction_core.payments.gateway import Checkout, Gateway, Transaction

HMAC_FIELDS = (
	"amount_cents",
	"created_at",
	"currency",
	"error_occured",
	"has_parent_transaction",
	"id",
	"integration_id",
	"is_3d_secure",
	"is_auth",
	"is_capture",
	"is_refunded",
	"is_standalone_payment",
	"is_voided",
	"order.id",
	"owner",
	"pending",
	"source_data.pan",
	"source_data.sub_type",
	"source_data.type",
	"success",
)
TIMEOUT = 20


def _get(obj: dict, dotted: str):
	cur = obj
	for part in dotted.split("."):
		if not isinstance(cur, dict):
			return None
		cur = cur.get(part)
	return cur


def _str(value) -> str:
	if isinstance(value, bool):
		return "true" if value else "false"
	return "" if value is None else str(value)


def hmac_string(obj: dict) -> str:
	return "".join(_str(_get(obj, f)) for f in HMAC_FIELDS)


def sign(obj: dict, secret: str) -> str:
	return hmac_lib.new(secret.encode(), hmac_string(obj).encode(), hashlib.sha512).hexdigest()


class Paymob(Gateway):
	name = "Paymob"

	def __init__(self, s):
		self.s = s
		self.base = (s.paymob_base_url or "https://accept.paymob.com").rstrip("/")

	def _secret(self, field: str) -> str:
		value = self.s.get_password(field, raise_exception=False)
		if not value:
			frappe.throw(_("Paymob is not set up in Settings"))
		return value

	def create_checkout(self, payment, client: dict) -> Checkout:
		methods = [
			i
			for i in (
				self.s.paymob_card_integration_id if payment.method == "Card" else None,
				self.s.paymob_wallet_integration_id if payment.method == "Wallet" else None,
			)
			if i
		]
		if not methods:
			frappe.throw(_("This payment method is not set up"))
		cents = int((Decimal(str(payment.amount)) * 100).to_integral_value())
		body = {
			"amount": cents,
			"currency": "EGP",
			"payment_methods": methods,
			"items": [{"name": payment.title[:50], "amount": cents, "quantity": 1}],
			"billing_data": {
				"first_name": client.get("first_name") or "-",
				"last_name": client.get("last_name") or "-",
				"email": client.get("email") or "na@example.invalid",
				"phone_number": client.get("phone") or "+200000000000",
			},
			"special_reference": payment.reference,
			"notification_url": get_url("/api/method/construction_core.api.public.paymob_webhook"),
			"redirection_url": get_url(f"/portal/c/{payment.project}/payments?ref={payment.reference}"),
		}
		r = requests.post(
			f"{self.base}/v1/intention/",
			json=body,
			headers={"Authorization": f"Token {self._secret('paymob_secret_key')}"},
			timeout=TIMEOUT,
		)
		if r.status_code >= 300:
			frappe.log_error(title="Paymob: create intention failed", message=r.text[:2000])
			frappe.throw(_("بوابة الدفع مش متاحة دلوقتي، جرّب تاني بعد شوية"))
		data = r.json()
		url = f"{self.base}/unifiedcheckout/?" + urlencode(
			{"publicKey": self.s.paymob_public_key, "clientSecret": data["client_secret"]}
		)
		return Checkout(url=url, gateway_order_id=str(data.get("intention_order_id") or ""))

	def verify_webhook(self, payload: dict, signature: str) -> bool:
		obj = payload.get("obj") if isinstance(payload, dict) else None
		if not isinstance(obj, dict) or not signature:
			return False
		expected = sign(obj, self._secret("paymob_hmac_secret"))
		return hmac_lib.compare_digest(expected, str(signature).lower())

	def parse_webhook(self, payload: dict) -> Transaction:
		return self._transaction(payload["obj"])

	def _transaction(self, obj: dict) -> Transaction:
		order = obj.get("order") or {}
		return Transaction(
			transaction_id=str(obj.get("id")),
			reference=str(order.get("merchant_order_id") or obj.get("special_reference") or ""),
			success=bool(obj.get("success")) and not obj.get("is_refunded") and not obj.get("is_voided"),
			pending=bool(obj.get("pending")),
			amount=Decimal(str(obj.get("amount_cents") or 0)) / 100,
			method=_get(obj, "source_data.type"),
		)

	def _auth_token(self) -> str:
		r = requests.post(
			f"{self.base}/api/auth/tokens", json={"api_key": self._secret("paymob_api_key")}, timeout=TIMEOUT
		)
		r.raise_for_status()
		return r.json()["token"]

	def inquire(self, payment) -> Transaction | None:
		r = requests.post(
			f"{self.base}/api/ecommerce/orders/transaction_inquiry",
			json={"merchant_order_id": payment.reference},
			headers={"Authorization": f"Bearer {self._auth_token()}"},
			timeout=TIMEOUT,
		)
		if r.status_code == 404:
			return None
		r.raise_for_status()
		return self._transaction(r.json())

	def refund(self, payment, amount: Decimal) -> str:
		r = requests.post(
			f"{self.base}/api/acceptance/void_refund/refund",
			json={
				"transaction_id": payment.transaction_id,
				"amount_cents": int((amount * 100).to_integral_value()),
			},
			headers={"Authorization": f"Token {self._secret('paymob_secret_key')}"},
			timeout=TIMEOUT,
		)
		if r.status_code >= 300:
			frappe.log_error(title="Paymob: refund failed", message=r.text[:2000])
			frappe.throw(_("البوابة رفضت الاسترداد"))
		return str(r.json().get("id") or "")
