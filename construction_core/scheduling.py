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
