"""Server-side tools for the assistant and the MCP connector (phase 18).

Every tool runs as the calling user and checks access itself: a project the user cannot see
raises PermissionError. Money figures come only from the phase 7 costing engine (`run_costing`
and the draft documents, which price themselves with the same engine). Draft tools create
Drafts only; nothing here approves, sends, signs or pays.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from construction_core import analytics
from construction_core.costing import engine
from construction_core.costing.engine import D, round2
from construction_core.permissions import assert_project_access, has_full_access, is_client

LINE_FIELDS = (
	"section",
	"line_type",
	"item",
	"assembly",
	"labor_type",
	"description",
	"qty",
	"uom",
	"unit_cost",
	"waste_pct",
)


def _staff():
	if frappe.session.user == "Guest" or is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)


def _money(value) -> str:
	return f"{flt(value, 2):.2f}"


def get_project_summary(project: str) -> dict:
	_staff()
	assert_project_access(project)
	p = frappe.get_doc("Project", project)
	stages = frappe.get_all(
		"Project Stage",
		filters={"project": project},
		fields=["stage_name", "status", "progress", "planned_end"],
		order_by="sort_order asc",
	)
	late = analytics.schedule_status({"project": project})
	return {
		"project": project,
		"name": p.project_name,
		"progress_pct": flt(p.weighted_progress, 2),
		"stages": [{**s, "planned_end": str(s.planned_end or "")} for s in stages],
		"days_late": late[0]["days_late"] if late else 0,
		"open_selections": frappe.db.count(
			"Project Selection", {"project": project, "status": ["in", ["Open", "Chosen"]]}
		),
		"pending_approvals": frappe.db.count(
			"Project Message", {"project": project, "kind": "Approval", "approval_status": "Pending"}
		),
		"draft_change_orders": frappe.db.count("Change Order", {"project": project, "status": "Draft"}),
	}


def get_rooms_and_measurements(project: str) -> dict:
	"""Rooms and quantities from approved estimates and takeoffs only."""
	_staff()
	assert_project_access(project)
	lines = frappe.db.sql(
		"""select l.name, l.section, l.line_type, l.item, l.assembly, l.description, l.qty, l.uom
		from `tabEstimate Line` l join `tabEstimate` e on e.name = l.parent
		where e.project = %s and e.docstatus = 1 and l.parenttype = 'Estimate' order by l.idx""",
		project,
		as_dict=True,
	)
	estimates = frappe.get_all("Estimate", filters={"project": project}, pluck="name")
	takeoffs = []
	for t in frappe.get_all(
		"Takeoff", filters={"estimate": ["in", estimates or ["-"]]}, fields=["name", "title"]
	):
		for m in frappe.get_all(
			"Takeoff Measurement", filters={"parent": t.name}, fields=["label", "kind", "value", "uom"]
		):
			takeoffs.append({"drawing": t.title, **m})
	return {"estimate_lines": lines, "takeoff_measurements": takeoffs}


def get_current_prices(items: list[str]) -> list[dict]:
	_staff()
	out = []
	today = nowdate()
	for code in (items or [])[:50]:
		row = frappe.get_all(
			"Item Price",
			filters={"item_code": code, "price_list": engine.BUYING_PRICE_LIST, "valid_from": ["<=", today]},
			fields=["price_list_rate", "valid_from", "price_source", "source_ref"],
			order_by="valid_from desc, creation desc",
			limit=1,
		)
		if row:
			out.append(
				{
					"item": code,
					"price": _money(row[0].price_list_rate),
					"valid_from": str(row[0].valid_from),
					"source": row[0].price_source,
					"source_ref": row[0].source_ref,
				}
			)
		else:
			out.append({"item": code, "price": None, "note": _("مفيش سعر مسجل")})
	return out


def _clean_lines(lines) -> list[dict]:
	lines = json.loads(lines) if isinstance(lines, str) else lines
	if not isinstance(lines, list) or not lines or len(lines) > 100:
		frappe.throw(_("Give between 1 and 100 lines"))
	clean = []
	for line in lines:
		row = {k: line.get(k) for k in LINE_FIELDS if line.get(k) not in (None, "")}
		row.setdefault("section", _("عام"))
		row.setdefault("line_type", "Other")
		if row["line_type"] not in ("Assembly", "Material", "Labor", "Equipment", "Other"):
			frappe.throw(_("Unknown line type"))
		# The model never sets a price: the engine looks it up (Other lines start at 0 for a person to fill)
		row.pop("unit_cost", None)
		row["qty"] = flt(row.get("qty"))
		clean.append(row)
	return clean


def run_costing(lines, overhead_pct: float = 0, profit_pct: float = 0) -> dict:
	"""The phase 7 engine: the only source of money figures."""
	_staff()
	clean = _clean_lines(lines)
	today = nowdate()
	parts = [engine.line_parts(frappe._dict(line), today) for line in clean]
	res = engine.compute(parts, overhead_pct, profit_pct, 0)
	return {
		"lines": [
			{
				"section": c["section"],
				"description": c.get("description")
				or c.get("item")
				or c.get("assembly")
				or c.get("labor_type"),
				"qty": c["qty"],
				"line_total": _money(t),
			}
			for c, t in zip(clean, res["line_totals"], strict=True)
		],
		"subtotal": _money(res["subtotal"]),
		"overhead": _money(round2(res["overhead"])),
		"profit": _money(round2(res["profit"])),
		"total": _money(res["grand_total"]),
	}


def draft_change_order(project: str, lines, description: str, title: str | None = None) -> dict:
	"""Creates a Draft change order (removals are negative quantities). Never sends it."""
	_staff()
	assert_project_access(project, "read")
	if not frappe.has_permission("Change Order", "create"):
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	co = frappe.get_doc(
		{
			"doctype": "Change Order",
			"project": project,
			"title": (title or description or _("تعديل"))[:140],
			"description": (description or "")[:4000],
			"source": "Office",
			"status": "Draft",
			"overhead_pct": 0,
			"profit_pct": 0,
			"lines": _clean_lines(lines),
		}
	)
	co.insert()
	return {
		"change_order": co.name,
		"status": co.status,
		"lines": [
			{
				"description": l.description or l.item or l.assembly,
				"qty": l.qty,
				"line_total": _money(l.line_total),
			}
			for l in co.lines
		],
		"total": _money(co.cost_difference),
	}


def draft_estimate(
	sections,
	customer: str | None = None,
	lead: str | None = None,
	project: str | None = None,
	title: str | None = None,
) -> dict:
	_staff()
	if not (has_full_access() or "Construction Sales" in frappe.get_roles()):
		frappe.throw(_("Only the office makes estimates"), frappe.PermissionError)
	if project:
		assert_project_access(project)
		customer = customer or frappe.db.get_value("Project", project, "customer")
	sections = json.loads(sections) if isinstance(sections, str) else sections
	lines = []
	for s in sections or []:
		for line in s.get("lines") or []:
			lines.append({**line, "section": s.get("section") or line.get("section")})
	est = frappe.get_doc(
		{
			"doctype": "Estimate",
			"title": (title or _("تسعير من المساعد"))[:140],
			"customer": customer,
			"lead": lead,
			"project": project,
			"estimate_date": nowdate(),
			"lines": _clean_lines(lines),
		}
	)
	est.insert()
	return {"estimate": est.name, "status": "Draft", "total": _money(est.grand_total)}


def summarize_daily_logs(project: str, from_date: str | None = None, to_date: str | None = None) -> dict:
	_staff()
	assert_project_access(project)
	filters = {"project": project}
	if from_date or to_date:
		filters["log_date"] = ["between", [getdate(from_date or "2000-01-01"), getdate(to_date or nowdate())]]
	logs = frappe.get_list(
		"Daily Log",
		filters=filters,
		fields=["log_date", "weather", "work_done", "issues"],
		order_by="log_date asc",
		limit_page_length=60,
	)
	return {"logs": [{**l, "log_date": str(l.log_date)} for l in logs]}


def explain_variance(project: str) -> dict:
	_staff()
	assert_project_access(project)
	return {
		"over_budget": analytics.budget_variance({"project": project}),
		"job_costing": analytics.job_costing({"project": project}),
	}


READ_ONLY = {
	"get_project_summary": get_project_summary,
	"get_rooms_and_measurements": get_rooms_and_measurements,
	"get_current_prices": get_current_prices,
	"run_costing": run_costing,
	"summarize_daily_logs": summarize_daily_logs,
	"explain_variance": explain_variance,
}
DRAFTS = {"draft_change_order": draft_change_order, "draft_estimate": draft_estimate}

_LINES = {
	"type": "array",
	"items": {
		"type": "object",
		"properties": {
			"section": {"type": "string"},
			"line_type": {"type": "string", "enum": ["Assembly", "Material", "Labor", "Equipment", "Other"]},
			"item": {"type": "string"},
			"assembly": {"type": "string"},
			"labor_type": {"type": "string"},
			"description": {"type": "string"},
			"qty": {"type": "number", "description": "negative to remove"},
		},
		"required": ["line_type", "qty"],
	},
}
SCHEMAS = {
	"get_project_summary": (
		"Progress, schedule and open items of a project.",
		{"project": {"type": "string"}},
		["project"],
	),
	"get_rooms_and_measurements": (
		"Rooms and quantities from approved estimates and takeoffs.",
		{"project": {"type": "string"}},
		["project"],
	),
	"get_current_prices": (
		"Current buying prices of items, with source and date.",
		{"items": {"type": "array", "items": {"type": "string"}}},
		["items"],
	),
	"run_costing": (
		"Price lines with the costing engine. The ONLY source of money figures.",
		{"lines": _LINES, "overhead_pct": {"type": "number"}, "profit_pct": {"type": "number"}},
		["lines"],
	),
	"summarize_daily_logs": (
		"Daily logs of a project in a date range.",
		{"project": {"type": "string"}, "from_date": {"type": "string"}, "to_date": {"type": "string"}},
		["project"],
	),
	"explain_variance": (
		"Budget variance and job costing of a project.",
		{"project": {"type": "string"}},
		["project"],
	),
	"draft_change_order": (
		"Create a DRAFT change order (removals are negative quantities).",
		{
			"project": {"type": "string"},
			"lines": _LINES,
			"description": {"type": "string"},
			"title": {"type": "string"},
		},
		["project", "lines", "description"],
	),
	"draft_estimate": (
		"Create a DRAFT estimate.",
		{
			"sections": {
				"type": "array",
				"items": {"type": "object", "properties": {"section": {"type": "string"}, "lines": _LINES}},
			},
			"customer": {"type": "string"},
			"lead": {"type": "string"},
			"project": {"type": "string"},
			"title": {"type": "string"},
		},
		["sections"],
	),
}


def tool_specs(include_drafts: bool = True) -> list[dict]:
	names = list(READ_ONLY) + (list(DRAFTS) if include_drafts else [])
	return [
		{
			"name": n,
			"description": SCHEMAS[n][0],
			"input_schema": {"type": "object", "properties": SCHEMAS[n][1], "required": SCHEMAS[n][2]},
		}
		for n in names
	]


def call_tool(name: str, args: dict, include_drafts: bool = True):
	fn = READ_ONLY.get(name) or (DRAFTS.get(name) if include_drafts else None)
	if not fn:
		frappe.throw(_("Unknown tool"))
	return fn(**(args or {}))
