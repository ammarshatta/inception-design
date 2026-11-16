"""Daily logs, GPS clock-in/out and timesheets (phase 12).

Privacy: location is captured only at clock-in and clock-out, only after the user has
accepted the Arabic consent text (its version is stored on every event). Egypt PDPL 151/2020.
"""

import math
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate, time_diff_in_hours

from construction_core.permissions import assert_project_access, is_client

EARTH_RADIUS_M = 6_371_000
ACTIVITY_TYPE = "عمالة موقع"


def haversine_m(lat1, lon1, lat2, lon2) -> float:
	"""Great-circle distance in metres."""
	p1, p2 = math.radians(lat1), math.radians(lat2)
	dp = p2 - p1
	dl = math.radians(lon2 - lon1)
	a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
	return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def inside_geofence(distance_m: float, radius_m: float) -> bool:
	return distance_m <= radius_m


def _require_staff():
	if is_client():
		frappe.throw(_("Not allowed"), frappe.PermissionError)


# --- Consent --------------------------------------------------------------------------


@frappe.whitelist()
def consent() -> dict:
	s = frappe.get_cached_doc("Inceptiondesign Settings")
	accepted = frappe.db.get_value("User", frappe.session.user, "clock_consent_version")
	return {
		"version": s.clock_consent_version,
		"text": s.clock_consent_text,
		"accepted": accepted == s.clock_consent_version,
		"enabled": bool(s.enable_gps_clock_in),
	}


@frappe.whitelist(methods=["POST"])
def accept_consent(version: str) -> dict:
	current = frappe.db.get_single_value("Inceptiondesign Settings", "clock_consent_version")
	if version != current:
		frappe.throw(_("نص الموافقة اتغير، اقراه تاني"))
	frappe.db.set_value("User", frappe.session.user, "clock_consent_version", current)
	return {"accepted": True}


# --- Clock in / out -------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def clock(
	project: str,
	event: str,
	workers: list | str,
	latitude: float | None = None,
	longitude: float | None = None,
	accuracy_m: float | None = None,
	device_info: str | None = None,
) -> list[str]:
	"""Clock a crew (or one worker) in or out. `workers`: [{employee?, crew?, worker}]."""
	_require_staff()
	assert_project_access(project)
	if event not in ("In", "Out"):
		frappe.throw(_("Unknown event"))
	if not frappe.db.get_single_value("Inceptiondesign Settings", "enable_gps_clock_in"):
		frappe.throw(_("Clock-in with location is turned off in Settings"))
	info = consent()
	if not info["accepted"]:
		frappe.throw(_("لازم توافق على تسجيل الموقع الأول"), frappe.PermissionError)
	workers = frappe.parse_json(workers) if isinstance(workers, str) else workers
	if not workers:
		frappe.throw(_("Choose at least one worker"))

	site = frappe.db.get_value(
		"Project", project, ["site_latitude", "site_longitude", "site_radius_m"], as_dict=True
	)
	has_location = latitude not in (None, "") and longitude not in (None, "")
	distance = None
	inside = False
	if has_location and site.site_latitude and site.site_longitude:
		distance = haversine_m(
			flt(latitude), flt(longitude), flt(site.site_latitude), flt(site.site_longitude)
		)
		inside = inside_geofence(distance, cint(site.site_radius_m) or 150)
	names = []
	for w in workers:
		doc = frappe.get_doc(
			{
				"doctype": "Clock Event",
				"project": project,
				"event": event,
				"at": now_datetime(),
				"employee": w.get("employee"),
				"crew": w.get("crew"),
				"worker": w.get("worker") or w.get("employee") or frappe.utils.get_fullname(),
				"recorded_by": frappe.session.user,
				"consent_version": info["version"],
				"device_info": (device_info or "")[:300],
				"latitude": flt(latitude) if has_location else None,
				"longitude": flt(longitude) if has_location else None,
				"accuracy_m": flt(accuracy_m) if accuracy_m else None,
				"distance_m": round(distance, 1) if distance is not None else None,
				"inside_geofence": 1 if inside else 0,
				"location_missing": 0 if has_location else 1,
				# Outside the radius, or with location off: recorded, flagged, needs engineer approval
				"needs_approval": 0 if inside else 1,
			}
		)
		doc.insert(ignore_permissions=True)
		names.append(doc.name)
	return names


@frappe.whitelist(methods=["POST"])
def approve_clock_event(name: str) -> None:
	doc = frappe.get_doc("Clock Event", name)
	assert_project_access(doc.project)
	if not set(frappe.get_roles()) & {"Construction Engineer", "Construction Admin", "System Manager"}:
		frappe.throw(_("Only the engineer approves"), frappe.PermissionError)
	frappe.db.set_value("Clock Event", name, {"needs_approval": 0, "approved_by": frappe.session.user})


# --- Pairing and timesheets -----------------------------------------------------------


def pair_events(events: list) -> tuple[list, list]:
	"""(pairs, unpaired_ins). `events` sorted by time for one worker and project.
	Each In is closed by the next Out; an In with no Out is unpaired (flagged, not counted)."""
	pairs, unpaired = [], []
	open_in = None
	for e in sorted(events, key=lambda x: get_datetime(x["at"])):
		if e["event"] == "In":
			if open_in:
				unpaired.append(open_in)
			open_in = e
		elif e["event"] == "Out" and open_in:
			pairs.append((open_in, e, round(time_diff_in_hours(e["at"], open_in["at"]), 2)))
			open_in = None
	if open_in:
		unpaired.append(open_in)
	return pairs, unpaired


def ensure_activity_type() -> str:
	if not frappe.db.exists("Activity Type", ACTIVITY_TYPE):
		frappe.get_doc({"doctype": "Activity Type", "activity_type": ACTIVITY_TYPE}).insert(
			ignore_permissions=True
		)
	return ACTIVITY_TYPE


def hourly_rate(employee: str) -> float:
	"""The crew member's daily rate ÷ hours per day, else the Activity Type costing rate."""
	daily = frappe.db.get_value("Crew Member", {"employee": employee, "active": 1}, "daily_rate")
	hours = flt(frappe.db.get_single_value("Inceptiondesign Settings", "labor_hours_per_day")) or 8
	if daily:
		return flt(flt(daily) / hours, 2)
	return flt(frappe.db.get_value("Activity Type", ACTIVITY_TYPE, "costing_rate"), 2)


def build_timesheets(on_date=None) -> list[str]:
	"""Nightly: draft ERPNext Timesheets from paired clock events, per employee per project."""
	on_date = getdate(on_date or add_days(nowdate(), -1))
	ensure_activity_type()
	events = frappe.get_all(
		"Clock Event",
		filters={
			"employee": ["is", "set"],
			"timesheet": ["is", "not set"],
			"needs_approval": 0,
			"at": ["between", [f"{on_date} 00:00:00", f"{on_date} 23:59:59"]],
		},
		fields=["name", "employee", "project", "event", "at"],
	)
	groups = defaultdict(list)
	for e in events:
		groups[(e.employee, e.project)].append(e)
	created = []
	for (employee, project), evs in groups.items():
		pairs, unpaired = pair_events(evs)
		for e in unpaired:
			frappe.db.set_value("Clock Event", e["name"], "unpaired", 1)
		if not pairs:
			continue
		rate = hourly_rate(employee)
		ts = frappe.get_doc(
			{
				"doctype": "Timesheet",
				"employee": employee,
				"company": frappe.db.get_value("Project", project, "company"),
				"time_logs": [
					{
						"activity_type": ACTIVITY_TYPE,
						"from_time": i["at"],
						"to_time": o["at"],
						"hours": hours,
						"project": project,
						"costing_rate": rate,
						"is_billable": 0,
					}
					for i, o, hours in pairs
				],
			}
		)
		ts.insert(ignore_permissions=True)
		for i, o, _h in pairs:
			frappe.db.set_value("Clock Event", i["name"], "timesheet", ts.name)
			frappe.db.set_value("Clock Event", o["name"], "timesheet", ts.name)
		created.append(ts.name)
	return created


# --- Daily log ------------------------------------------------------------------------


@frappe.whitelist()
def get_daily_log(project: str, log_date: str | None = None) -> dict:
	"""One log per project per day: opens today's log, or a new one with yesterday's defaults."""
	_require_staff()
	assert_project_access(project)
	log_date = getdate(log_date or nowdate())
	name = frappe.db.get_value("Daily Log", {"project": project, "log_date": log_date}, "name")
	if name:
		return {
			"exists": True,
			**frappe.get_doc("Daily Log", name).as_dict(no_default_fields=True),
			"name": name,
		}
	prev = frappe.get_all(
		"Daily Log",
		filters={"project": project, "log_date": ["<", log_date]},
		order_by="log_date desc",
		limit=1,
		pluck="name",
	)
	defaults = {"project": project, "log_date": str(log_date), "weather": "صافي", "manpower": []}
	if prev:
		p = frappe.get_doc("Daily Log", prev[0])
		defaults["weather"] = p.weather
		defaults["manpower"] = [
			{
				"crew": m.crew,
				"supplier": m.supplier,
				"trade": m.trade,
				"headcount": m.headcount,
				"hours": m.hours,
			}
			for m in p.manpower
		]
	return {"exists": False, **defaults}


@frappe.whitelist(methods=["POST"])
def save_daily_log(project: str, data: dict | str) -> str:
	_require_staff()
	assert_project_access(project)
	data = frappe.parse_json(data) if isinstance(data, str) else data
	log_date = getdate(data.get("log_date") or nowdate())
	name = frappe.db.get_value("Daily Log", {"project": project, "log_date": log_date}, "name")
	doc = frappe.get_doc("Daily Log", name) if name else frappe.new_doc("Daily Log")
	doc.project = project
	doc.log_date = log_date
	for f in ("weather", "work_done", "issues", "visitors", "equipment"):
		if f in data:
			doc.set(f, data.get(f))
	doc.internal_only = cint(data.get("internal_only"))
	if "manpower" in data:
		doc.set("manpower", [])
		for m in data["manpower"] or []:
			doc.append("manpower", {k: m.get(k) for k in ("crew", "supplier", "trade", "headcount", "hours")})
	if "materials_used" in data:
		doc.set("materials_used", [])
		for m in data["materials_used"] or []:
			doc.append(
				"materials_used",
				{k: m.get(k) for k in ("item", "description", "qty", "uom", "project_stage")},
			)
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def client_daily_logs(project: str) -> list[dict]:
	"""What the client sees: work done and photos of non-internal logs. No manpower, no costs."""
	assert_project_access(project)
	rows = frappe.get_all(
		"Daily Log",
		filters={"project": project, "internal_only": 0},
		fields=["name", "log_date", "weather", "work_done"],
		order_by="log_date desc",
		limit=60,
	)
	for r in rows:
		r.photos = frappe.get_all(
			"Stage Update Media",
			filters={"parent": r.name, "parenttype": "Daily Log", "kind": "Photo"},
			pluck="file",
		)
		del r["name"]
	return rows


@frappe.whitelist()
def week_summary(project: str, week_end: str | None = None) -> dict:
	"""Weekly summary for the client: days worked, progress, photos (no costs)."""
	assert_project_access(project)
	end = getdate(week_end or nowdate())
	start = add_days(end, -6)
	logs = frappe.get_all(
		"Daily Log",
		filters={"project": project, "internal_only": 0, "log_date": ["between", [start, end]]},
		fields=["log_date", "work_done"],
		order_by="log_date asc",
	)
	return {
		"from": str(start),
		"to": str(end),
		"days_worked": len(logs),
		"progress": flt(frappe.db.get_value("Project", project, "weighted_progress")),
		"days": logs,
	}
