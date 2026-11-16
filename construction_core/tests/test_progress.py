"""Weighted progress, auto progress, template copy, milestones (P01-03, P01-04)."""

import frappe
from frappe.tests import IntegrationTestCase

from construction_core.construction_core.doctype.project_stage.project_stage import (
	auto_progress,
	get_weight_summary,
	weighted_progress,
)
from construction_core.tests.factories import (
	TEMPLATE_NAME,
	TEMPLATE_STAGES,
	make_milestone,
	make_project,
	make_update,
	make_world,
	stages_of,
)


class TestCalculations(IntegrationTestCase):
	def test_weighted_progress_example(self):
		# stage A weight 5 Done (100%), stage B weight 30 at 50%, the rest at 0% → 20.0%
		stages = [
			{"weight": 5, "progress": 100},
			{"weight": 30, "progress": 50},
			{"weight": 65, "progress": 0},
		]
		self.assertEqual(weighted_progress(stages), 20.0)

	def test_weighted_progress_zero_weights(self):
		self.assertEqual(weighted_progress([{"weight": 0, "progress": 50}]), 0.0)

	def test_auto_progress(self):
		rows = [frappe._dict(done=1), frappe._dict(done=1), frappe._dict(done=1), frappe._dict(done=0)]
		self.assertEqual(auto_progress(rows), 75.0)
		self.assertEqual(auto_progress([]), 0.0)


class TestStagesOnProject(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()

	def test_template_copied(self):
		names = stages_of(self.w.p1)
		self.assertEqual(len(names), len(TEMPLATE_STAGES))
		first = frappe.get_doc("Project Stage", names[0])
		self.assertEqual(first.stage_name, TEMPLATE_STAGES[0][0])
		self.assertEqual(first.weight, TEMPLATE_STAGES[0][1])
		self.assertEqual([r.label for r in first.checklist], TEMPLATE_STAGES[0][2].split("\n"))

	def test_template_edit_does_not_change_project(self):
		project = make_project("مشروع اختبار القالب", [])
		template = frappe.get_doc("Phase Template", TEMPLATE_NAME)
		original = (template.stages[0].stage_name, template.stages[0].weight)
		try:
			template.stages[0].stage_name = "اسم جديد"
			template.stages[0].weight = 99
			template.save(ignore_permissions=True)
			first = frappe.get_doc("Project Stage", stages_of(project)[0])
			self.assertEqual(first.stage_name, TEMPLATE_STAGES[0][0])
			self.assertEqual(first.weight, TEMPLATE_STAGES[0][1])
		finally:
			template.reload()
			template.stages[0].stage_name, template.stages[0].weight = original
			template.save(ignore_permissions=True)

	def test_auto_stage_three_of_four(self):
		project = make_project("مشروع اختبار الأوتو", [])
		stage = frappe.get_doc("Project Stage", stages_of(project)[2])  # 4 checklist items
		self.assertEqual(len(stage.checklist), 4)
		for row in stage.checklist[:3]:
			row.done = 1
		stage.save(ignore_permissions=True)
		self.assertEqual(stage.progress, 75.0)
		self.assertEqual(stage.checklist[0].done_by, frappe.session.user)

	def test_project_progress_example(self):
		project = make_project("مشروع اختبار الأوزان", [], with_template=False)
		a = frappe.get_doc(
			{
				"doctype": "Project Stage",
				"project": project,
				"stage_name": "A",
				"weight": 5,
				"progress_mode": "Manual",
				"progress": 100,
				"status": "Done",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Project Stage",
				"project": project,
				"stage_name": "B",
				"weight": 30,
				"progress_mode": "Manual",
				"progress": 50,
				"status": "In Progress",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Project Stage",
				"project": project,
				"stage_name": "C",
				"weight": 65,
				"progress_mode": "Manual",
				"progress": 0,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Project", project, "weighted_progress"), 20.0)
		self.assertTrue(a.actual_end)

	def test_weight_warning(self):
		project = make_project("مشروع اختبار التحذير", [], with_template=False)
		frappe.get_doc(
			{"doctype": "Project Stage", "project": project, "stage_name": "A", "weight": 90}
		).insert(ignore_permissions=True)
		summary = get_weight_summary(project)
		self.assertEqual(summary["total_weight"], 90)
		self.assertFalse(summary["ok"])

	def test_done_stage_moves_milestone_to_due(self):
		project = make_project("مشروع اختبار الدفعات", [])
		stage_name = stages_of(project)[0]
		milestone = make_milestone(project, stage_name, 5000)
		self.assertEqual(frappe.db.get_value("Payment Milestone", milestone, "status"), "Upcoming")
		stage = frappe.get_doc("Project Stage", stage_name)
		stage.status = "Done"
		stage.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Payment Milestone", milestone, "status"), "Due")

	def test_manual_stage_takes_update_progress(self):
		project = make_project("مشروع اختبار اليدوي", [])
		stage = frappe.get_doc("Project Stage", stages_of(project)[3])
		stage.progress_mode = "Manual"
		stage.save(ignore_permissions=True)
		doc = frappe.get_doc(
			{
				"doctype": "Stage Update",
				"project": project,
				"project_stage": stage.name,
				"text": "x",
				"progress_after": 60,
			}
		).insert(ignore_permissions=True)
		self.assertTrue(doc.name)
		self.assertEqual(frappe.db.get_value("Project Stage", stage.name, "progress"), 60.0)

	def test_update_stage_must_belong_to_project(self):
		other_stage = stages_of(self.w.p2)[0]
		self.assertRaises(frappe.ValidationError, make_update, self.w.p1, other_stage)
