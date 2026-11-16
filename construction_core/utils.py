"""Small shared helpers."""

from contextlib import contextmanager

import frappe


@contextmanager
def as_system():
	"""Run system follow-ups of a user action (project kickoff, change order effects) as
	Administrator, then switch back. The user's own action was already permission-checked."""
	user = frappe.session.user
	if user == "Administrator":
		yield
		return
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(user)
