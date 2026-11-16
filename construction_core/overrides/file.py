"""Every file attached to a construction_core record is private (phase 1, task 1).

Exception: the office logo in Inceptiondesign Settings, which public pages show.
Public copies of publishable photos are made separately in phase 5.
"""

from construction_core.permissions import SCOPED_DOCTYPES

PRIVATE_DOCTYPES = frozenset(
	{
		*SCOPED_DOCTYPES,
		"Phase Template",
		"Design Template",
	}
)
PUBLIC_EXCEPTIONS = frozenset({("Inceptiondesign Settings", "logo")})


def before_insert(doc, method=None):
	if doc.flags.public_copy:  # media.make_public_copy: an intentional public copy
		return
	key = (doc.attached_to_doctype, doc.attached_to_field)
	if key in PUBLIC_EXCEPTIONS:
		return
	if doc.attached_to_doctype in PRIVATE_DOCTYPES or doc.attached_to_doctype == "Inceptiondesign Settings":
		doc.is_private = 1
