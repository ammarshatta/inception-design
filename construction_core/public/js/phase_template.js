// Phase Template: weight total under the stages table, warning when it is not 100.
frappe.ui.form.on("Phase Template", {
	refresh: (frm) => construction_template.show_total(frm),
	validate: (frm) => construction_template.show_total(frm),
});
frappe.ui.form.on("Phase Template Stage", {
	weight: (frm) => construction_template.show_total(frm),
	stages_remove: (frm) => construction_template.show_total(frm),
});

window.construction_template = {
	show_total(frm) {
		const total = (frm.doc.stages || []).reduce((sum, row) => sum + flt(row.weight), 0);
		const ok = Math.abs(total - 100) < 0.001;
		const html = `<div class="${ok ? "text-muted" : "text-warning"}" style="margin-top:6px">
			${__("مجموع الأوزان")}: <b>${format_number(total, null, 2)}</b>
			${ok ? "" : " — " + __("Stage weights add up to {0}, not 100.", [format_number(total, null, 2)])}
		</div>`;
		const grid = frm.get_field("stages").$wrapper;
		grid.find(".weight-total").remove();
		grid.append(`<div class="weight-total">${html}</div>`);
	},
};
