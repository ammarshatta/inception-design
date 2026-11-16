frappe.query_reports["CC Budget Variance"] = {
	filters: [
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project" },
		{ fieldname: "engineer", label: __("المهندس"), fieldtype: "Link", options: "User" },
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date" },
		{ fieldname: "threshold_pct", label: __("أكتر من %"), fieldtype: "Percent", default: 10 },
	],
};
