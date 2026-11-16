// Company calendar of all assignments (phase 11): filter by crew, subcontractor, project.
frappe.views.calendar["Crew Assignment"] = {
	field_map: {
		start: "from_date",
		end: "to_date",
		id: "name",
		title: "title",
		allDay: "allDay",
	},
	filters: ["crew", "supplier", "project", "status"],
	gantt: true,
};
