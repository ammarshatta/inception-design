frappe.query_reports["CC Selections Status"] = {
	filters: [
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project" },
		{ fieldname: "engineer", label: __("المهندس"), fieldtype: "Link", options: "User" },
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date" },
	],
};
