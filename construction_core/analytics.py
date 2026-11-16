"""Numbers for the phase 17 reports and the manager dashboard.

Every function takes the report filters and works on the projects the current user may see
(`allowed_projects`, which goes through Frappe's permission query: an engineer only gets the
projects they are a member of). Queries are grouped per report, never one query per project,
so 200 projects stay well under 3 seconds.

WIP (أعمال تحت التنفيذ), per project:
- contract       = Σ payment milestones (approved change orders add or reduce milestones)
- complete       = weighted progress (phase 1)
- earned value   = contract × complete
- billed         = Σ submitted sales invoices (returns included)
- over/under     = billed − earned (positive: billed ahead of the work)
- cost to date   = Σ submitted purchase invoice items (net) + submitted timesheet cost
- cost at completion (EAC) = cost to date ÷ complete, or the budget while nothing is complete
- projected margin = contract − EAC
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

P = 2  # money precision


def allowed_projects(filters=None) -> list[str]:
	filters = frappe._dict(filters or {})
	f = {}
	if filters.get("project"):
		f["name"] = filters.project
	if filters.get("company"):
		f["company"] = filters.company
	if filters.get("status"):
		f["status"] = filters.status
	names = frappe.get_list("Project", filters=f, pluck="name", limit_page_length=0)
	if filters.get("engineer"):
		members = set(
			frappe.get_all(
				"Project User", filters={"user": filters.engineer, "parenttype": "Project"}, pluck="parent"
			)
		)
		names = [n for n in names if n in members]
	return names


def _in(projects: list[str]) -> tuple:
	return tuple(projects) or ("__none__",)


def _sum_by_project(sql: str, projects, *extra) -> dict:
	return {r[0]: flt(r[1], P) for r in frappe.db.sql(sql, (_in(projects), *extra))}


def _date_cond(field: str, filters) -> tuple[str, list]:
	cond, args = "", []
	if filters.get("from_date"):
		cond += f" and {field} >= %s"
		args.append(filters.from_date)
	if filters.get("to_date"):
		cond += f" and {field} <= %s"
		args.append(filters.to_date)
	return cond, args


# --- WIP ------------------------------------------------------------------------------


def wip_math(contract, complete_pct, billed, cost, budget) -> dict:
	contract, billed, cost, budget = flt(contract, P), flt(billed, P), flt(cost, P), flt(budget, P)
	ratio = flt(complete_pct) / 100
	earned = flt(contract * ratio, P)
	eac = flt(cost / ratio, P) if ratio > 0 else budget
	margin = flt(contract - eac, P)
	return {
		"contract": contract,
		"complete": flt(complete_pct, 2),
		"earned": earned,
		"billed": billed,
		"over_under": flt(billed - earned, P),
		"cost": cost,
		"eac": eac,
		"margin": margin,
		"margin_pct": flt(100 * margin / contract, 2) if contract else 0,
	}


def wip(filters=None) -> list[dict]:
	filters = frappe._dict(filters or {})
	projects = allowed_projects({**filters, "status": filters.get("status") or "Open"})
	if not projects:
		return []
	info = {
		r.name: r
		for r in frappe.get_all(
			"Project",
			filters={"name": ["in", projects]},
			fields=[
				"name",
				"project_name",
				"weighted_progress",
				"estimated_costing",
				"total_costing_amount",
				"company",
			],
		)
	}
	contract = _sum_by_project(
		"select project, sum(amount) from `tabPayment Milestone` where project in %s group by project",
		projects,
	)
	billed = _sum_by_project(
		"""select project, sum(if(disable_rounded_total = 1 or base_rounded_total = 0, base_grand_total,
			base_rounded_total)) from `tabSales Invoice` where docstatus = 1 and project in %s group by project""",
		projects,
	)
	purchases = _sum_by_project(
		"""select coalesce(nullif(pii.project, ''), pi.project) p, sum(pii.base_net_amount)
		from `tabPurchase Invoice Item` pii join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and coalesce(nullif(pii.project, ''), pi.project) in %s group by p""",
		projects,
	)
	rounding = _sum_by_project(
		"""select project, sum(base_rounding_adjustment) from `tabPurchase Invoice`
		where docstatus = 1 and project in %s group by project""",
		projects,
	)
	rows = []
	for name in projects:
		p = info.get(name)
		if not p:
			continue
		cost = flt(purchases.get(name)) + flt(rounding.get(name)) + flt(p.total_costing_amount)
		row = wip_math(contract.get(name), p.weighted_progress, billed.get(name), cost, p.estimated_costing)
		rows.append({"project": name, "project_name": p.project_name, **row})
	return sorted(rows, key=lambda r: r["project_name"] or r["project"])


# --- Job costing ----------------------------------------------------------------------

TYPE_BY_GROUP = {"خامات": "material", "عمالة": "labor", "معدات": "equipment", "نقل": "other"}
TYPE_LABEL = {
	"material": "خامات",
	"labor": "عمالة",
	"subcontract": "مقاولين باطن",
	"equipment": "معدات",
	"other": "أخرى",
}


def job_costing(filters=None) -> list[dict]:
	"""Budget vs committed vs actual by project, stage and type."""
	from construction_core.construction_core.report.committed_cost.committed_cost import get_data as committed
	from construction_core.subcontracts import SUBCONTRACT_ITEM

	filters = frappe._dict(filters or {})
	projects = allowed_projects(filters)
	if not projects:
		return []
	cells = defaultdict(lambda: {"budget": 0.0, "committed": 0.0, "actual": 0.0})
	stage_names = dict(
		frappe.db.sql("select name, stage_name from `tabProject Stage` where project in %s", (_in(projects),))
	)
	stage_by_section = {
		(r[0], r[1]): r[2]
		for r in frappe.db.sql(
			"select project, stage_name, name from `tabProject Stage` where project in %s", (_in(projects),)
		)
	}
	# budget: approved estimates' cost parts by section (= stage made at kickoff)
	for r in frappe.db.sql(
		"""select e.project, l.section, sum(l.material_part), sum(l.labor_part), sum(l.equipment_part),
			sum(l.other_part)
		from `tabEstimate Line` l join `tabEstimate` e on e.name = l.parent
		where e.docstatus = 1 and e.project in %s group by e.project, l.section""",
		(_in(projects),),
	):
		stage = stage_by_section.get((r[0], r[1]))
		for kind, value in zip(("material", "labor", "equipment", "other"), r[2:], strict=True):
			cells[(r[0], stage, kind)]["budget"] += flt(value, P)
	# committed: open purchase orders (material) and unclaimed subcontract lines (subcontract)
	for row in committed(frappe._dict()):
		if row["project"] not in projects:
			continue
		kind = "subcontract" if row["doctype"] == "Subcontract" else "material"
		cells[(row["project"], row["project_stage"], kind)]["committed"] += flt(row["committed"], P)
	# actual: purchase invoice items by item group; subcontract claims by their item
	date_cond, date_args = _date_cond("pi.posting_date", filters)
	for r in frappe.db.sql(
		f"""select coalesce(nullif(pii.project, ''), pi.project) p,
			coalesce(nullif(pii.project_stage, ''), pi.project_stage) s, pii.item_group, pii.item_code,
			sum(pii.base_net_amount)
		from `tabPurchase Invoice Item` pii join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and coalesce(nullif(pii.project, ''), pi.project) in %s {date_cond}
		group by p, s, pii.item_group, pii.item_code""",
		(_in(projects), *date_args),
	):
		kind = "subcontract" if r[3] == SUBCONTRACT_ITEM else TYPE_BY_GROUP.get(r[2], "other")
		cells[(r[0], r[1], kind)]["actual"] += flt(r[4], P)
	# actual labour from submitted timesheets (stage through the task)
	date_cond, date_args = _date_cond("td.from_time", filters)
	for r in frappe.db.sql(
		f"""select td.project, t.project_stage, sum(td.costing_amount)
		from `tabTimesheet Detail` td join `tabTimesheet` ts on ts.name = td.parent
		left join `tabTask` t on t.name = td.task
		where ts.docstatus = 1 and td.project in %s {date_cond} group by td.project, t.project_stage""",
		(_in(projects), *date_args),
	):
		cells[(r[0], r[1], "labor")]["actual"] += flt(r[2], P)
	rows = []
	for (project, stage, kind), v in cells.items():
		rows.append(
			{
				"project": project,
				"project_stage": stage,
				"stage_name": stage_names.get(stage) or _("بدون مرحلة"),
				"type": TYPE_LABEL[kind],
				"budget": flt(v["budget"], P),
				"committed": flt(v["committed"], P),
				"actual": flt(v["actual"], P),
				"remaining": flt(v["budget"] - v["committed"] - v["actual"], P),
			}
		)
	return sorted(rows, key=lambda r: (r["project"], r["stage_name"], r["type"]))


def budget_variance(filters=None) -> list[dict]:
	filters = frappe._dict(filters or {})
	threshold = flt(filters.get("threshold_pct") or 10)
	rows = []
	reasons = defaultdict(list)
	for r in frappe.get_all(
		"Change Order",
		filters={"docstatus": 1, "project": ["in", _in(allowed_projects(filters))]},
		fields=["project", "title", "source"],
	):
		reasons[r.project].append(f"{r.title} ({_(r.source or '')})")
	for r in job_costing(filters):
		spent = r["actual"] + r["committed"]
		if r["budget"] <= 0 and spent <= 0:
			continue
		over = flt(spent - r["budget"], P)
		pct = flt(100 * over / r["budget"], 2) if r["budget"] else 100.0
		if pct > threshold:
			rows.append(
				{
					**r,
					"spent": flt(spent, P),
					"over": over,
					"over_pct": pct,
					"reasons": "، ".join(reasons[r["project"]]),
				}
			)
	return rows


# --- Labour ---------------------------------------------------------------------------


def labor(filters=None) -> list[dict]:
	filters = frappe._dict(filters or {})
	projects = allowed_projects(filters)
	if not projects:
		return []
	hours_per_day = flt(frappe.db.get_single_value("Inceptiondesign Settings", "labor_hours_per_day")) or 8
	crew_of = dict(
		frappe.db.sql("select employee, parent from `tabCrew Member` where ifnull(employee, '') != ''")
	)
	date_cond, date_args = _date_cond("date(td.from_time)", filters)
	rows = {}
	daily = defaultdict(float)
	for r in frappe.db.sql(
		f"""select td.project, ts.employee, ts.employee_name, date(td.from_time) d, sum(td.hours), sum(td.costing_amount)
		from `tabTimesheet Detail` td join `tabTimesheet` ts on ts.name = td.parent
		where ts.docstatus = 1 and td.project in %s {date_cond}
		group by td.project, ts.employee, ts.employee_name, d""",
		(_in(projects), *date_args),
	):
		key = (r[0], r[1])
		row = rows.setdefault(
			key,
			{
				"project": r[0],
				"employee": r[1],
				"employee_name": r[2],
				"crew": crew_of.get(r[1]),
				"hours": 0.0,
				"cost": 0.0,
				"overtime": 0.0,
				"flagged": 0,
			},
		)
		row["hours"] += flt(r[4], 2)
		row["cost"] += flt(r[5], P)
		daily[(r[1], r[3])] += flt(r[4], 2)
		row["overtime"] += max(flt(r[4], 2) - hours_per_day, 0)
	date_cond, date_args = _date_cond("date(at)", filters)
	for r in frappe.db.sql(
		f"""select project, employee, count(*) from `tabClock Event`
		where project in %s and (needs_approval = 1 or inside_geofence = 0) {date_cond}
		group by project, employee""",
		(_in(projects), *date_args),
	):
		row = rows.setdefault(
			(r[0], r[1]),
			{
				"project": r[0],
				"employee": r[1],
				"employee_name": r[1],
				"crew": crew_of.get(r[1]),
				"hours": 0.0,
				"cost": 0.0,
				"overtime": 0.0,
				"flagged": 0,
			},
		)
		row["flagged"] += int(r[2])
	for row in rows.values():
		row["hours"], row["cost"], row["overtime"] = (
			flt(row["hours"], 2),
			flt(row["cost"], P),
			flt(row["overtime"], 2),
		)
	return sorted(rows.values(), key=lambda r: (r["project"], r["crew"] or "", r["employee"] or ""))


# --- Sales ----------------------------------------------------------------------------


def pipeline(filters=None) -> dict:
	filters = frappe._dict(filters or {})
	date_cond, date_args = _date_cond("o.creation", filters)
	company_cond = " and o.company = %s" if filters.get("company") else ""
	args = [*date_args] + ([filters.company] if filters.get("company") else [])
	stages = frappe.db.sql(
		f"""select ifnull(o.pipeline_stage, ''), count(*), sum(o.opportunity_amount)
		from `tabOpportunity` o where 1=1 {date_cond}{company_cond} group by o.pipeline_stage""",
		args,
	)
	status = dict(
		frappe.db.sql(
			f"select o.status, count(*) from `tabOpportunity` o where 1=1 {date_cond}{company_cond} group by o.status",
			args,
		)
	)
	won = int(status.get("Converted", 0))
	lost = int(status.get("Lost", 0)) + int(status.get("Closed", 0))
	reasons = frappe.db.sql(
		f"""select r.lost_reason, count(*) from `tabOpportunity Lost Reason Detail` r
		join `tabOpportunity` o on o.name = r.parent where 1=1 {date_cond}{company_cond} group by r.lost_reason""",
		args,
	)
	sources = frappe.db.sql(
		f"select ifnull(o.utm_source, ''), count(*) from `tabOpportunity` o where 1=1 {date_cond}{company_cond} group by o.utm_source",
		args,
	)
	avg_estimate = frappe.db.sql(
		f"""select avg(e.grand_total) from `tabEstimate` e join `tabOpportunity` o on o.name = e.opportunity
		where e.docstatus < 2 and ifnull(e.previous_revision, '') = '' {date_cond}{company_cond}""",
		args,
	)[0][0]
	return {
		"stages": [
			{"stage": s[0] or _("بدون مرحلة"), "count": int(s[1]), "value": flt(s[2], P)} for s in stages
		],
		"won": won,
		"lost": lost,
		"conversion": flt(100 * won / (won + lost), 2) if (won + lost) else 0,
		"lost_reasons": [{"reason": r[0], "count": int(r[1])} for r in reasons],
		"sources": [{"source": s[0] or _("غير محدد"), "count": int(s[1])} for s in sources],
		"avg_estimate": flt(avg_estimate, P),
		"open_value": flt(sum(flt(s[2]) for s in stages), P),
	}


# --- Collections ----------------------------------------------------------------------


def collections(filters=None) -> list[dict]:
	"""Receivable aging per customer (from submitted invoices' outstanding) + upcoming milestones."""
	filters = frappe._dict(filters or {})
	projects = allowed_projects(filters)
	today = getdate(filters.get("to_date") or nowdate())
	rows = defaultdict(
		lambda: {
			"0-30": 0.0,
			"31-60": 0.0,
			"61-90": 0.0,
			"90+": 0.0,
			"outstanding": 0.0,
			"overdue": 0.0,
			"next_30": 0.0,
			"next_60": 0.0,
		}
	)
	company_cond = " and company = %s" if filters.get("company") else ""
	args = [_in(projects)] + ([filters.company] if filters.get("company") else [])
	for customer, project, due, outstanding in frappe.db.sql(
		f"""select customer, project, ifnull(due_date, posting_date), outstanding_amount from `tabSales Invoice`
		where docstatus = 1 and outstanding_amount != 0 and project in %s {company_cond}""",
		args,
	):
		age = date_diff(today, due)
		bucket = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "90+"
		r = rows[(customer, project)]
		r[bucket] += flt(outstanding, P)
		r["outstanding"] += flt(outstanding, P)
		if age > 0:
			r["overdue"] += flt(outstanding, P)
	for project, due, amount, customer in frappe.db.sql(
		"""select m.project, m.due_date, m.amount, p.customer from `tabPayment Milestone` m
		join `tabProject` p on p.name = m.project
		where m.status in ('Upcoming', 'Due') and ifnull(m.sales_invoice, '') = '' and m.due_date between %s and %s
			and m.project in %s""",
		(today, add_days(today, 60), _in(projects)),
	):
		r = rows[(customer, project)]
		r["next_60"] += flt(amount, P)
		if date_diff(due, today) <= 30:
			r["next_30"] += flt(amount, P)
	return [
		{"customer": c, "project": p, **{k: flt(v, P) for k, v in r.items()}}
		for (c, p), r in sorted(rows.items(), key=lambda x: (x[0][0] or "", x[0][1] or ""))
	]


# --- Selections and schedule ----------------------------------------------------------


def selections_status(filters=None) -> list[dict]:
	filters = frappe._dict(filters or {})
	projects = allowed_projects(filters)
	today = nowdate()
	out = defaultdict(lambda: {"open": 0, "awaiting": 0, "approved": 0, "overdue": 0})
	for project, status, due in frappe.db.sql(
		"select project, status, due_date from `tabProject Selection` where project in %s and status != 'Superseded'",
		(_in(projects),),
	):
		r = out[project]
		if status in ("Open", "Chosen"):
			r["open"] += 1
			if due and str(due) < today:
				r["overdue"] += 1
		elif status == "Awaiting Signature":
			r["awaiting"] += 1
		else:
			r["approved"] += 1
	names = dict(
		frappe.db.sql("select name, project_name from tabProject where name in %s", (_in(projects),))
	)
	return [{"project": p, "project_name": names.get(p), **v} for p, v in sorted(out.items())]


def schedule_status(filters=None) -> list[dict]:
	"""Projects behind schedule: the worst stage that is past its planned end and not Done."""
	filters = frappe._dict(filters or {})
	projects = allowed_projects({**filters, "status": "Open"})
	today = getdate(nowdate())
	worst = {}
	for project, stage, end, progress in frappe.db.sql(
		"""select project, stage_name, planned_end, progress from `tabProject Stage`
		where project in %s and status != 'Done' and planned_end is not null and planned_end < %s""",
		(_in(projects), today),
	):
		days = date_diff(today, end)
		if days > worst.get(project, {}).get("days_late", 0):
			worst[project] = {
				"days_late": days,
				"stage": stage,
				"planned_end": end,
				"progress": flt(progress, 2),
			}
	names = dict(
		frappe.db.sql("select name, project_name from tabProject where name in %s", (_in(projects),))
	)
	return sorted(
		[{"project": p, "project_name": names.get(p), **v} for p, v in worst.items()],
		key=lambda r: -r["days_late"],
	)


# --- Dashboard ------------------------------------------------------------------------


def dashboard(filters=None) -> dict:
	w = wip(filters)
	c = collections(filters)
	return {
		"active_projects": len(w),
		"over_under": flt(sum(r["over_under"] for r in w), P),
		"receivables": flt(sum(r["outstanding"] for r in c), P),
		"overdue": flt(sum(r["overdue"] for r in c), P),
		"late_projects": len(schedule_status(filters)),
		"pipeline_value": pipeline(filters)["open_value"],
	}


# --- Engineer dashboard (portal) and the owner's weekly summary -------------------------


@frappe.whitelist()
def engineer_dashboard() -> dict:
	"""The engineer's own priorities: only projects they are a member of (permission query)."""
	from construction_core.permissions import is_client

	if is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	projects = allowed_projects({"status": "Open"})
	today = nowdate()
	tasks = frappe.get_all(
		"Task",
		filters={
			"project": ["in", _in(projects)],
			"status": ["not in", ["Completed", "Cancelled", "Template"]],
			"exp_start_date": ["<=", today],
			"exp_end_date": [">=", today],
		},
		fields=["name", "subject", "project", "exp_end_date"],
		order_by="exp_end_date asc",
		limit=50,
	)
	overdue = frappe.get_all(
		"Project Selection",
		filters={
			"project": ["in", _in(projects)],
			"status": ["in", ["Open", "Chosen"]],
			"due_date": ["<", today],
		},
		fields=["name", "title", "project", "due_date"],
		order_by="due_date asc",
	)
	approvals = frappe.get_all(
		"Project Message",
		filters={"project": ["in", _in(projects)], "kind": "Approval", "approval_status": "Pending"},
		fields=["name", "approval_title", "project", "creation"],
		order_by="creation asc",
	)
	changes = frappe.get_all(
		"Change Order",
		filters={"project": ["in", _in(projects)], "status": "Draft", "source": "Client Request"},
		fields=["name", "title", "project", "creation"],
	)
	names = dict(
		frappe.db.sql("select name, project_name from tabProject where name in %s", (_in(projects),))
	)
	for rows in (tasks, overdue, approvals, changes):
		for r in rows:
			r.project_name = names.get(r.project)
	return {
		"projects": len(projects),
		"late": schedule_status({})[:10],
		"tasks_today": tasks,
		"overdue_selections": overdue,
		"pending_approvals": approvals,
		"client_requests": changes,
	}


def owner_summary() -> dict:
	"""Data for the weekly PDF (jinja method)."""
	with_admin = frappe.session.user
	return {
		"dashboard": dashboard({}),
		"wip": wip({})[:30],
		"late": schedule_status({})[:15],
		"collections": collections({})[:20],
		"generated_by": with_admin,
	}


SUMMARY_PRINT_FORMAT = "Inceptiondesign Weekly Summary"


def send_weekly_summary():
	"""Saturday 9 AM (hooks cron): the owner gets the summary PDF by email."""
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}):
		return None
	owners = frappe.get_all(
		"Has Role",
		filters={"role": "Construction Admin", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	emails = [
		e
		for e in frappe.get_all(
			"User", filters={"name": ["in", owners or ["-"]], "enabled": 1}, pluck="email"
		)
		if e and not e.endswith(".invalid")
	]
	if not emails:
		return None
	pdf = frappe.get_print(
		"Inceptiondesign Settings",
		"Inceptiondesign Settings",
		print_format=SUMMARY_PRINT_FORMAT,
		as_pdf=True,
		no_letterhead=1,
	)
	frappe.sendmail(
		recipients=emails,
		subject=_("ملخص الأسبوع"),
		message=_("الملخص الأسبوعي مرفق."),
		attachments=[{"fname": "weekly-summary.pdf", "fcontent": pdf}],
		now=False,
	)
	return emails
