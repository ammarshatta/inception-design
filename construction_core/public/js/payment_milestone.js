// "اعمل فاتورة" on a Due milestone (phase 6): a draft Sales Invoice for the accountant to review.
frappe.ui.form.on("Payment Milestone", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Due") return;
		frm.add_custom_button(__("اعمل فاتورة"), () => {
			frappe
				.call({ method: "construction_core.money.make_invoice", args: { milestone: frm.doc.name }, freeze: true })
				.then(({ message }) => frappe.set_route("Form", "Sales Invoice", message));
		}).addClass("btn-primary");
	},
});
