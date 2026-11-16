// "أجّل": move a task and every dependent task by N working days, with a preview (phase 11).
frappe.ui.form.on("Task", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.exp_start_date) return;
		frm.add_custom_button(__("أجّل"), () => {
			frappe.prompt(
				{ fieldname: "days", fieldtype: "Int", label: __("عدد أيام الشغل"), reqd: 1, default: 1 },
				({ days }) => {
					const args = { task: frm.doc.name, days };
					frappe.call("construction_core.scheduling.slide_task", { ...args, apply: 0 }).then(({ message }) => {
						const rows = message
							.map((r) => `<tr><td>${frappe.utils.escape_html(r.subject)}</td><td>${r.from[0]} → ${r.from[1]}</td><td>${r.to[0]} → ${r.to[1]}</td></tr>`)
							.join("");
						frappe.confirm(
							`<table class="table table-sm"><tr><th>${__("المهمة")}</th><th>${__("من")}</th><th>${__("إلى")}</th></tr>${rows}</table>`,
							() =>
								frappe
									.call("construction_core.scheduling.slide_task", { ...args, apply: 1 })
									.then(() => frm.reload_doc())
						);
					});
				},
				__("أجّل المهمة واللي بعدها"),
				__("معاينة")
			);
		});
	},
});
