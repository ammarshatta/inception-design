"""Writes the phase 19 security review tables from the code (run: python scripts/security_review.py).

- every @frappe.whitelist method, whether it allows guests, and the access checks found in its body
- every ignore_permissions=True / flags.ignore_permissions with its file and line
"""

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1] / "construction_core"
CHECKS = (
	"assert_project_access",
	"check_permission",
	"has_permission",
	"_require",
	"has_full_access",
	"is_client",
	"_staff",
	"_get_for_signer",
	"_milestone_for_client",
	"_stage_project",
	"_get_update_for_write",
	"verify_webhook",
	"allow_tests",
	"session.user",
	"_get_project",
	"_selection_for_client",
	"get_list",
	"get_roles",
	"_require_user",
	"_require_office",
	"_require_purchasing",
	"_require_accounts",
	"_require_admin",
	"_require_staff",
)


def whitelisted(node):
	for d in node.decorator_list:
		target = d.func if isinstance(d, ast.Call) else d
		if isinstance(target, ast.Attribute) and target.attr == "whitelist":
			guest = isinstance(d, ast.Call) and any(
				k.arg == "allow_guest" and getattr(k.value, "value", False) for k in d.keywords
			)
			return True, guest
	return False, False


rows, ignores = [], []
for path in sorted(ROOT.rglob("*.py")):
	if "tests" in path.parts:
		continue
	src = path.read_text()
	rel = path.relative_to(ROOT.parent)
	for i, line in enumerate(src.splitlines(), 1):
		if "ignore_permissions=True" in line or "ignore_permissions = True" in line:
			ignores.append((str(rel), i, line.strip()[:110]))
	# Python 3.14 allows `except A, B:`; add the brackets so older parsers can read it too
	parsable = re.sub(r"except ([\w.]+(?:, [\w.]+)+):", r"except (\1):", src)
	for node in ast.walk(ast.parse(parsable)):
		if isinstance(node, ast.FunctionDef):
			ok, guest = whitelisted(node)
			if ok:
				body = ast.get_source_segment(parsable, node) or ""
				found = sorted({c for c in CHECKS if c in body})
				rows.append((str(rel), node.name, guest, ", ".join(found) or "—"))

print("| File | Method | Guest | Access checks found in the body |\n|---|---|---|---|")
for f, n, g, c in rows:
	print(f"| `{f}` | `{n}` | {'**yes**' if g else 'no'} | {c} |")
print(f"\n{len(rows)} whitelisted methods; guest methods only in: {sorted({f for f, _n, g, _c in rows if g})}\n")
print("| File | Line | Code |\n|---|---|---|")
for f, i, line in ignores:
	print(f"| `{f}` | {i} | `{line.replace('|', '\\|')}` |")
