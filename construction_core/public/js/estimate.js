// Estimate: actions for revisions, comparison, quotation, and starting from a design.
frappe.ui.form.on("Estimate", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("قياس من الرسم"), () =>
				window.open(`/portal/takeoff?estimate=${encodeURIComponent(frm.doc.name)}`, "_blank")
			);
		}
		if (frm.doc.docstatus === 1 && frm.doc.status === "Approved") {
			frm.add_custom_button(__("مراجعة جديدة"), () =>
				frappe.call("construction_core.sales.revise", { estimate: frm.doc.name }).then(({ message }) =>
					frappe.set_route("Form", "Estimate", message)
				)
			);
			if (!frm.doc.quotation) {
				frm.add_custom_button(__("اعمل عرض سعر"), () =>
					frappe.call("construction_core.sales.make_quotation", { estimate: frm.doc.name }).then(({ message }) =>
						frappe.set_route("Form", "Quotation", message)
					)
				).addClass("btn-primary");
			}
		}
		if (frm.doc.previous_revision) {
			frm.add_custom_button(__("قارن بالمراجعة السابقة"), () =>
				frappe
					.call("construction_core.sales.compare_revisions", { a: frm.doc.previous_revision, b: frm.doc.name })
					.then(({ message }) => construction_estimate.show_diff(message))
			);
		}
		if (frm.is_new() || frm.doc.docstatus === 0) {
			frm.add_custom_button(__("ابدأ من تصميم"), () => {
				frappe.prompt(
					{ fieldname: "design", fieldtype: "Link", options: "Design Template", label: __("التصميم"), reqd: 1 },
					(v) =>
						frappe
							.call("construction_core.sales.estimate_from_design", {
								design: v.design,
								customer: frm.doc.customer,
								lead: frm.doc.lead,
							})
							.then(({ message }) => frappe.set_route("Form", "Estimate", message))
				);
			});
		}
	},
});

window.construction_estimate = {
	show_diff(d) {
		const esc = frappe.utils.escape_html;
		const row = (r, extra = "") =>
			`<tr><td>${esc(r.section)}</td><td>${esc(r.ref)}</td><td class="text-right">${format_currency(r.line_total)}</td><td class="text-right">${extra}</td></tr>`;
		const html = `
			<h5>${__("بنود اتضافت")} (${format_currency(d.added_total)})</h5>
			<table class="table table-sm">${d.added.map((r) => row(r)).join("") || "<tr><td>—</td></tr>"}</table>
			<h5>${__("بنود اتشالت")} (${format_currency(d.removed_total)})</h5>
			<table class="table table-sm">${d.removed.map((r) => row(r)).join("") || "<tr><td>—</td></tr>"}</table>
			<h5>${__("بنود اتغيرت")}</h5>
			<table class="table table-sm">${d.changed.map((r) => row(r, format_currency(r.difference))).join("") || "<tr><td>—</td></tr>"}</table>
			<p><b>${__("فرق الإجمالي النهائي")}: ${format_currency(d.grand_total_difference)}</b></p>`;
		frappe.msgprint({ title: __("مقارنة المراجعات"), message: html, wide: true });
	},
};
