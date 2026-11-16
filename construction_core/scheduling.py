"""Schedule helpers shared by change orders (phase 10) and scheduling (phase 11)."""

import frappe
from frappe.utils import add_days, cint


def shift_dates(start, end, days: int):
	"""Both dates moved by `days` (None stays None)."""
	return (add_days(start, days) if start else None, add_days(end, days) if end else None)


def shift_stages(project: str, from_stage: str | None, days: int) -> list[str]:
	"""Move `from_stage` and every later stage (by sort order) and their tasks by `days`.

	Returns the moved stage names. Done stages are never moved.
	"""
	days = cint(days)
	if not days:
		return []
	stages = frappe.get_all(
		"Project Stage",
		filters={"project": project},
		fields=["name", "stage_name", "sort_order", "planned_start", "planned_end", "status"],
		order_by="sort_order asc, creation asc",
	)
	start_index = 0
	if from_stage:
		names = [s.name for s in stages]
		start_index = names.index(from_stage) if from_stage in names else 0
	moved = []
	for s in stages[start_index:]:
		if s.status == "Done" or not (s.planned_start or s.planned_end):
			continue
		new_start, new_end = shift_dates(s.planned_start, s.planned_end, days)
		frappe.db.set_value("Project Stage", s.name, {"planned_start": new_start, "planned_end": new_end})
		for task in frappe.get_all(
			"Task",
			filters={"project": project, "subject": s.stage_name, "status": ["!=", "Completed"]},
			fields=["name", "exp_start_date", "exp_end_date"],
		):
			t_start, t_end = shift_dates(task.exp_start_date, task.exp_end_date, days)
			frappe.db.set_value("Task", task.name, {"exp_start_date": t_start, "exp_end_date": t_end})
		moved.append(s.name)
	return moved


# --- Phase 11: working days, task slide, stage roll-up ---------------------------------

from datetime import date, timedelta

from frappe import _
from frappe.utils import getdate

HOLIDAY_LIST = "إجازات المقاولات"
# Fixed-date Egyptian public holidays (Islamic holidays move each year: the office adds them).
FIXED_HOLIDAYS = [(1, 7), (1, 25), (4, 25), (5, 1), (6, 30), (7, 23), (10, 6)]


def ensure_holiday_list(year: int | None = None) -> str:
	"""Fridays plus the fixed public holidays for the year."""
	year = year or getdate().year
	if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
		doc = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": HOLIDAY_LIST,
				"from_date": date(year, 1, 1),
				"to_date": date(year + 1, 12, 31),
			}
		)
		doc.insert(ignore_permissions=True)
	doc = frappe.get_doc("Holiday List", HOLIDAY_LIST)
	existing = {getdate(h.holiday_date) for h in doc.holidays}
	d = getdate(doc.from_date)
	end = getdate(doc.to_date)
	while d <= end:
		if d not in existing:
			if (d.month, d.day) in FIXED_HOLIDAYS:
				doc.append("holidays", {"holiday_date": d, "description": "إجازة رسمية"})
				existing.add(d)
			elif d.weekday() == 4:  # Friday
				doc.append("holidays", {"holiday_date": d, "description": "الجمعة", "weekly_off": 1})
				existing.add(d)
		d += timedelta(days=1)
	doc.save(ignore_permissions=True)
	return doc.name


def holidays(holiday_list: str | None = None) -> set:
	holiday_list = holiday_list or HOLIDAY_LIST
	if not frappe.db.exists("Holiday List", holiday_list):
		return set()
	return {
		getdate(d)
		for d in frappe.get_all(
			"Holiday", filters={"parent": holiday_list, "parenttype": "Holiday List"}, pluck="holiday_date"
		)
	}


def add_working_days(start, days: int, off: set | None = None):
	"""`start` moved by `days` working days (skipping Fridays and holidays in `off`).
	A start that falls on a day off first moves to the next working day."""
	off = holidays() if off is None else off
	d = getdate(start)
	step = 1 if days >= 0 else -1

	def is_off(x):
		return x in off or (not off and x.weekday() == 4)

	remaining = abs(cint(days))
	while remaining:
		d += timedelta(days=step)
		if not is_off(d):
			remaining -= 1
	while is_off(d):
		d += timedelta(days=1)
	return d


def dependents(task: str) -> list[str]:
	"""Every task that depends on `task`, directly or through others (breadth first)."""
	out, queue, seen = [], [task], {task}
	while queue:
		current = queue.pop(0)
		for parent in frappe.get_all(
			"Task Depends On", filters={"task": current, "parenttype": "Task"}, pluck="parent"
		):
			if parent not in seen:
				seen.add(parent)
				out.append(parent)
				queue.append(parent)
	return out


@frappe.whitelist()
def slide_task(task: str, days: int, apply: int = 0) -> list[dict]:
	""" "أجّل": move a task and every dependent task by N working days. Preview unless `apply`."""
	if not set(frappe.get_roles()) & {
		"System Manager",
		"Construction Admin",
		"Construction Engineer",
		"Projects Manager",
	}:
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	off = holidays()
	plan = []
	for name in [task, *dependents(task)]:
		t = frappe.db.get_value(
			"Task", name, ["name", "subject", "project", "exp_start_date", "exp_end_date"], as_dict=True
		)
		if not t.exp_start_date:
			continue
		new_start = add_working_days(t.exp_start_date, days, off)
		new_end = add_working_days(t.exp_end_date or t.exp_start_date, days, off)
		plan.append(
			{
				"task": t.name,
				"subject": t.subject,
				"project": t.project,
				"from": [str(t.exp_start_date), str(t.exp_end_date)],
				"to": [str(new_start), str(new_end)],
			}
		)
	if cint(apply):
		for row in reversed(plan):  # dependents first, so ERPNext's dependency checks stay valid
			doc = frappe.get_doc("Task", row["task"])
			doc.exp_start_date, doc.exp_end_date = row["to"]
			doc.save()
		_notify_slide(plan, days)
	return plan


def _notify_slide(plan, days):
	from construction_core.notifications import _clients, _notify

	tasks = [r["task"] for r in plan]
	foremen = frappe.get_all(
		"Crew Assignment", filters={"task": ["in", tasks], "status": "Planned"}, pluck="crew"
	)
	users = [frappe.db.get_value("Crew", c, "foreman_user") for c in set(foremen) if c]
	for project in {r["project"] for r in plan if r["project"]}:
		_notify(
			[*users, *_clients(project)],
			_("الجدول اتأجّل {0} يوم شغل").format(days),
			"Project",
			project,
		)


def task_on_update(doc, method=None):
	"""Roll task dates up to their stage: stage planned dates = min start / max end of its tasks."""
	if not doc.get("project_stage"):
		return
	rows = frappe.get_all(
		"Task",
		filters={"project_stage": doc.project_stage, "status": ["!=", "Cancelled"]},
		fields=["exp_start_date", "exp_end_date"],
	)
	starts = [getdate(r.exp_start_date) for r in rows if r.exp_start_date]
	ends = [getdate(r.exp_end_date) for r in rows if r.exp_end_date]
	values = {}
	if starts:
		values["planned_start"] = min(starts)
	if ends:
		values["planned_end"] = max(ends)
	if values:
		frappe.db.set_value("Project Stage", doc.project_stage, values)


# --- Crew conflicts and the foreman's view -------------------------------------------


def overlapping(assignment) -> list[dict]:
	filters = {
		"name": ["!=", assignment.name or ""],
		"status": ["!=", "Cancelled"],
		"from_date": ["<=", assignment.to_date],
		"to_date": [">=", assignment.from_date],
	}
	if assignment.crew:
		filters["crew"] = assignment.crew
	elif assignment.supplier:
		filters["supplier"] = assignment.supplier
	else:
		return []
	return frappe.get_all(
		"Crew Assignment", filters=filters, fields=["name", "project", "from_date", "to_date"]
	)


@frappe.whitelist()
def foreman_assignments(scope: str = "today") -> list[dict]:
	"""شغلي النهارده / الأسبوع ده: assignments of the crews this foreman leads."""
	crews = frappe.get_all("Crew", filters={"foreman_user": frappe.session.user, "active": 1}, pluck="name")
	if not crews:
		return []
	today = getdate()
	end = today if scope == "today" else today + timedelta(days=6)
	rows = frappe.get_all(
		"Crew Assignment",
		filters={
			"crew": ["in", crews],
			"status": "Planned",
			"from_date": ["<=", end],
			"to_date": [">=", today],
		},
		fields=["name", "crew", "project", "task", "from_date", "to_date", "notes"],
		order_by="from_date asc",
	)
	for r in rows:
		p = frappe.db.get_value(
			"Project",
			r.project,
			["project_name", "site_address", "site_latitude", "site_longitude"],
			as_dict=True,
		)
		r.project_name = p.project_name
		r.address = p.site_address or ""
		if p.site_latitude and p.site_longitude:
			r.map_url = f"https://www.google.com/maps?q={p.site_latitude},{p.site_longitude}"
		elif p.site_address:
			from urllib.parse import quote

			r.map_url = "https://www.google.com/maps/search/?api=1&query=" + quote(p.site_address)
		else:
			r.map_url = ""
		r.task_subject = frappe.db.get_value("Task", r.task, "subject") if r.task else ""
	return rows
