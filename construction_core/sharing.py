"""Secret share links for projects (phase 2, task 3; story P02-06).

Only the SHA-256 of the token is stored. The full link is shown once.
"""

import hashlib
import hmac
import secrets

import frappe
from frappe.utils import get_datetime, get_url, now_datetime


def hash_token(token: str) -> str:
	return hashlib.sha256((token or "").encode()).hexdigest()


def new_token() -> str:
	return secrets.token_urlsafe(16)


def share_url(project: str, token: str) -> str:
	return get_url(f"/p/{project}?t={token}")


def check_share_token(project: str, token: str | None) -> bool:
	"""True only for a project published by link whose current token matches and has not expired."""
	if not project or not token:
		return False
	row = frappe.db.get_value(
		"Project", project, ["visibility", "share_token_hash", "share_expires_at"], as_dict=True
	)
	if not row or row.visibility not in ("link", "public") or not row.share_token_hash:
		return False
	if row.share_expires_at and get_datetime(row.share_expires_at) <= now_datetime():
		return False
	return hmac.compare_digest(row.share_token_hash, hash_token(token))
