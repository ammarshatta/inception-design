"""Takeoff from drawings (phase 14).

The browser sends points in image pixels; the server recomputes every value from the points
and the calibration line, so a measurement can be checked and never trusted from the client.

- scale  = calibration line length in px ÷ its real length in metres
- length = Σ segment lengths ÷ scale                        (metres)
- area   = |shoelace(points)| ÷ scale²                       (square metres)
- count  = number of points
"""

import json
import math

import frappe
from frappe import _
from frappe.utils import flt

from construction_core.permissions import has_full_access

UOM = {"Length": "م", "Area": "م²", "Count": "عدد"}
OFFICE_ROLES = {"Construction Sales", "Construction Admin", "System Manager"}


def _require_office():
	if not (has_full_access() or OFFICE_ROLES & set(frappe.get_roles())):
		frappe.throw(_("Only the office can do takeoffs"), frappe.PermissionError)


def _points(value) -> list[tuple[float, float]]:
	pts = json.loads(value) if isinstance(value, str) else (value or [])
	if not isinstance(pts, list) or len(pts) > 2000:
		frappe.throw(_("Invalid points"))
	return [(float(p[0]), float(p[1])) for p in pts]


def polyline_length(points) -> float:
	return sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def shoelace_area(points) -> float:
	n = len(points)
	if n < 3:
		return 0.0
	s = sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1] for i in range(n))
	return abs(s) / 2


def scale_px_per_m(calibration_points, real_m: float) -> float:
	if len(calibration_points) != 2 or flt(real_m) <= 0:
		frappe.throw(_("Draw the calibration line and enter its real length"))
	px = math.dist(calibration_points[0], calibration_points[1])
	if px <= 0:
		frappe.throw(_("The calibration line is empty"))
	return px / flt(real_m)


def measure(kind: str, points, scale: float) -> float:
	if kind == "Length":
		return polyline_length(points) / scale
	if kind == "Area":
		return shoelace_area(points) / (scale * scale)
	if kind == "Count":
		return float(len(points))
	frappe.throw(_("Unknown measurement"))


def compute(doc):
	"""Fill scale, values and units on a Takeoff document."""
	doc.scale_px_per_m = scale_px_per_m(_points(doc.calibration_json), doc.calibration_m)
	for m in doc.measurements:
		m.value = round(measure(m.kind, _points(m.points_json), doc.scale_px_per_m), 3)
		m.uom = UOM[m.kind]


@frappe.whitelist(methods=["POST"])
def save_takeoff(data) -> dict:
	_require_office()
	data = frappe.parse_json(data) if isinstance(data, str) else data
	if data.get("name"):
		doc = frappe.get_doc("Takeoff", data["name"])
		doc.check_permission("write")
	else:
		doc = frappe.new_doc("Takeoff")
	for f in ("title", "project", "estimate", "drawing", "drawing_file", "page", "calibration_m"):
		if f in data:
			doc.set(f, data[f])
	doc.calibration_json = json.dumps(data.get("calibration") or [])
	keep = {m.name: m.estimate_line for m in doc.measurements}
	doc.set("measurements", [])
	for m in data.get("measurements") or []:
		doc.append(
			"measurements",
			{
				"label": str(m.get("label") or "")[:140],
				"kind": m.get("kind"),
				"points_json": json.dumps(m.get("points") or []),
				"estimate_line": keep.get(m.get("name")) or m.get("estimate_line"),
			},
		)
	doc.save() if doc.name and not doc.is_new() else doc.insert()
	return get_takeoff(doc.name)


@frappe.whitelist()
def get_takeoff(name: str) -> dict:
	_require_office()
	doc = frappe.get_doc("Takeoff", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"title": doc.title,
		"project": doc.project,
		"estimate": doc.estimate,
		"drawing_file": doc.drawing_file,
		"page": doc.page,
		"calibration": json.loads(doc.calibration_json or "[]"),
		"calibration_m": doc.calibration_m,
		"scale_px_per_m": doc.scale_px_per_m,
		"measurements": [
			{
				"name": m.name,
				"label": m.label,
				"kind": m.kind,
				"points": json.loads(m.points_json or "[]"),
				"value": m.value,
				"uom": m.uom,
				"estimate_line": m.estimate_line,
			}
			for m in doc.measurements
		],
	}


@frappe.whitelist(methods=["POST"])
def push_to_estimate(
	takeoff: str, measurement: str, estimate: str | None = None, line: str | None = None
) -> dict:
	"""أضف للتسعير: the measured value becomes the quantity of an estimate line (draft estimates
	only). With no line given, a new "Other" line is added for the office to complete."""
	_require_office()
	tk = frappe.get_doc("Takeoff", takeoff)
	tk.check_permission("write")
	m = next((r for r in tk.measurements if r.name == measurement), None)
	if not m:
		frappe.throw(_("Measurement not found"))
	estimate = estimate or tk.estimate
	if not estimate:
		frappe.throw(_("Choose an estimate"))
	est = frappe.get_doc("Estimate", estimate)
	est.check_permission("write")
	if est.docstatus != 0:
		frappe.throw(_("The estimate is approved: make a revision first"))
	qty = flt(m.value, 3)
	if line:
		row = next((r for r in est.lines if r.name == line), None)
		if not row:
			frappe.throw(_("Line not found"))
		row.qty = qty
	else:
		row = est.append(
			"lines",
			{
				"section": _("من الرسم"),
				"line_type": "Other",
				"description": m.label or _("قياس {0}").format(m.uom),
				"qty": qty,
				"unit_cost": 0,
			},
		)
	est.save()
	m.estimate_line = row.name
	tk.estimate = estimate
	tk.save()
	return {"estimate": est.name, "line": row.name, "qty": qty}
