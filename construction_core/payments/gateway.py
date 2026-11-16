"""Provider-neutral payment gateway interface (phase 15).

An adapter implements four calls. Amounts are Decimal pounds in, integer piastres on the wire.
Nothing here reads secrets from git: keys live in `Inceptiondesign Settings` (Password fields,
encrypted in the site database).
"""

from dataclasses import dataclass
from decimal import Decimal

import frappe
from frappe import _


@dataclass
class Checkout:
	url: str
	gateway_order_id: str


@dataclass
class Transaction:
	transaction_id: str
	reference: str  # our Online Payment reference (special_reference / merchant_order_id)
	success: bool
	pending: bool
	amount: Decimal
	method: str | None = None


class Gateway:
	name = "base"

	def create_checkout(self, payment, client: dict) -> Checkout:
		raise NotImplementedError

	def verify_webhook(self, payload: dict, signature: str) -> bool:
		raise NotImplementedError

	def parse_webhook(self, payload: dict) -> Transaction:
		raise NotImplementedError

	def inquire(self, payment) -> Transaction | None:
		raise NotImplementedError

	def refund(self, payment, amount: Decimal) -> str:
		raise NotImplementedError


def settings():
	return frappe.get_cached_doc("Inceptiondesign Settings")


def is_dev_site() -> bool:
	conf = frappe.conf
	host = (conf.get("host_name") or "") + " " + (frappe.local.site or "")
	return bool(
		conf.get("developer_mode") or conf.get("allow_tests") or "localhost" in host or ".local" in host
	)


def get_gateway() -> Gateway:
	s = settings()
	if not s.enable_online_payments:
		frappe.throw(_("الدفع أونلاين مقفول"))
	if s.gateway_mode == "Live" and is_dev_site():
		# rule: live keys are never used on a development or test site
		frappe.throw(_("Live payment keys cannot be used on a development or test site"))
	if (s.payment_gateway or "Paymob") == "Paymob":
		from construction_core.payments.paymob import Paymob

		return Paymob(s)
	frappe.throw(_("Unknown payment gateway"))
