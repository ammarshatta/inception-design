// Warn when the stage weights of a project do not add up to 100 (story P01-03, AC 3).
frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new()) return;
		frappe
			.call("construction_core.construction_core.doctype.project_stage.project_stage.get_weight_summary", {
				project: frm.doc.name,
			})
			.then(({ message }) => {
				if (message && !message.ok) {
					frm.dashboard.set_headline_alert(
						__("Stage weights add up to {0}, not 100.", [message.total_weight]),
						"orange"
					);
				}
			});
	},
});
