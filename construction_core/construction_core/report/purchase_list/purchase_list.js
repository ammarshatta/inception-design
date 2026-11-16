frappe.query_reports["Purchase List"] = {
	filters: [{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project", reqd: 1 }],
};
