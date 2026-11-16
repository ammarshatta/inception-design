# Copyright (c) 2026, Inceptiondesign and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today


class ProjectStage(Document):
	def validate(self):
		self.validate_weight()
		self.stamp_checklist()
		self.compute_progress()
		self.set_dates_from_status()

	def validate_weight(self):
		if flt(self.weight) < 0:
			frappe.throw(_("Stage weight cannot be negative"))

	def stamp_checklist(self):
		before = self.get_doc_before_save()
		was_done = {row.name: row.done for row in (before.checklist if before else [])}
		for row in self.checklist:
			if row.done and not was_done.get(row.name):
				row.done_by = frappe.session.user
				row.done_on = now_datetime()
			elif not row.done:
				row.done_by = None
				row.done_on = None

	def compute_progress(self):
		if self.progress_mode == "Auto":
			self.progress = auto_progress(self.checklist)
		self.progress = min(max(flt(self.progress, 2), 0), 100)

	def set_dates_from_status(self):
		if self.status in ("In Progress", "Done") and not self.actual_start:
			self.actual_start = today()
		if self.status == "Done":
			if not self.actual_end:
				self.actual_end = today()
		elif self.actual_end:
			self.actual_end = None
		if self.actual_start and self.actual_end and getdate(self.actual_end) < getdate(self.actual_start):
			frappe.throw(_("Actual end cannot be before actual start"))

	def on_update(self):
		update_project_progress(self.project)
		if self.status == "Done" and self.has_value_changed("status"):
			mark_milestones_due(self.name)

	def on_trash(self):
		self.flags.recompute_project = self.project

	def after_delete(self):
		update_project_progress(self.project)


def auto_progress(checklist) -> float:
	"""Done items ÷ all items × 100. With zero items, progress is 0."""
	total = len(checklist or [])
	if not total:
		return 0.0
	done = sum(1 for row in checklist if row.done)
	return flt(done * 100.0 / total, 2)


def weighted_progress(stages) -> float:
	"""Σ(weight × progress) ÷ Σ(weight). Returns 0 when the weights add up to 0."""
	total_weight = sum(flt(s.get("weight")) for s in stages)
	if not total_weight:
		return 0.0
	return flt(sum(flt(s.get("weight")) * flt(s.get("progress")) for s in stages) / total_weight, 2)


def update_project_progress(project: str | None) -> float | None:
	if not project:
		return None
	stages = frappe.get_all(
		"Project Stage", filters={"project": project}, fields=["weight", "progress"], ignore_permissions=True
	)
	value = weighted_progress(stages)
	frappe.db.set_value("Project", project, "weighted_progress", value, update_modified=False)
	return value


def mark_milestones_due(stage: str) -> None:
	"""When a stage becomes Done, its Upcoming payment milestones become Due."""
	for name in frappe.get_all(
		"Payment Milestone",
		filters={"project_stage": stage, "status": "Upcoming"},
		pluck="name",
		ignore_permissions=True,
	):
		milestone = frappe.get_doc("Payment Milestone", name)
		milestone.status = "Due"
		milestone.flags.ignore_permissions = True
		milestone.save()


@frappe.whitelist()
def get_weight_summary(project: str) -> dict:
	"""Used by the Project form to warn when the stage weights do not total 100."""
	from construction_core.permissions import assert_project_access

	assert_project_access(project)
	weights = frappe.get_all(
		"Project Stage", filters={"project": project}, pluck="weight", ignore_permissions=True
	)
	total = flt(sum(flt(w) for w in weights), 2)
	return {"stages": len(weights), "total_weight": total, "ok": not weights or total == 100}
