frappe.query_reports["Project Financial Summary"] = {
	filters: [
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project", reqd: 1 },
	],
};
