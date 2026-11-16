frappe.query_reports["CC Sales Pipeline"] = {
	filters: [
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date" },
	],
};
