"""Office branding comes only from `Inceptiondesign Settings` (CLAUDE.md rule 15).

Templates, emails, PDFs and the portal call `get_branding()`; nothing hardcodes the
office name, logo, colors or phone numbers.
"""

import frappe

SETTINGS = "Inceptiondesign Settings"
DEFAULT_PRIMARY = "#1D6B57"
DEFAULT_SECONDARY = "#17201D"

FEATURE_FLAGS = (
	"enable_selections",
	"enable_gps_clock_in",
	"enable_online_payments",
	"enable_ai_assistant",
	"enable_public_catalog",
)


def get_branding() -> dict:
	"""Branding values safe to show on any page (public or private)."""
	s = frappe.get_cached_doc(SETTINGS)
	office_name = s.office_name or frappe.db.get_single_value("Website Settings", "app_name") or ""
	return {
		"office_name": office_name,
		"logo": s.logo or "",
		"primary_color": s.primary_color or DEFAULT_PRIMARY,
		"secondary_color": s.secondary_color or DEFAULT_SECONDARY,
		"whatsapp_number": s.whatsapp_number or "",
	}


def get_feature_flags() -> dict:
	s = frappe.get_cached_doc(SETTINGS)
	return {flag: bool(s.get(flag)) for flag in FEATURE_FLAGS}


def is_enabled(flag: str) -> bool:
	if flag not in FEATURE_FLAGS:
		raise ValueError(f"Unknown feature flag: {flag}")
	return bool(frappe.get_cached_doc(SETTINGS).get(flag))
