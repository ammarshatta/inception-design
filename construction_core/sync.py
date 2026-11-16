"""Offline queue on the server side (phase 16).

The portal stores actions in IndexedDB while offline and sends them in order when back online.
Every action carries a UUID made on the phone. `apply` runs an action at most once per UUID:
the result is stored in a Sync Receipt (its name is the UUID, so a second insert of the same
UUID fails at the database), and a repeat returns the stored result. A browser closed in the
middle of a sync therefore resends safely.

Conflicts:
- stage updates, photos, clock events: append-only, they cannot conflict;
- daily log: one per project per day, fields merged (the last write wins);
- checklist: the server wins when the item changed on the server after the phone's tick.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, now_datetime

ACTIONS = {"create_update", "attach_media", "tick", "save_daily_log", "clock"}
MAX_AGE_DAYS = 14


class Rejected(frappe.ValidationError):
	pass


def _receipt(uuid: str):
	row = frappe.db.get_value("Sync Receipt", uuid, ["user", "result"], as_dict=True)
	if row and row.user != frappe.session.user:
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	return row


def _resolve(uuid_or_name: str, doctype: str) -> str:
	"""An action may point at a record made by an earlier queued action (by its UUID)."""
	if uuid_or_name and frappe.db.exists(doctype, uuid_or_name):
		return uuid_or_name
	row = _receipt(uuid_or_name)
	if not row:
		raise Rejected(_("The record this depends on was not synced yet"))
	return json.loads(row.result)["name"]


def _client_time(value):
	if not value:
		return None
	t = get_datetime(value)
	now = now_datetime()
	if t > now:
		return now
	if t < add_days(now, -MAX_AGE_DAYS):
		raise Rejected(_("This item is older than {0} days").format(MAX_AGE_DAYS))
	return t


def _run(action: str, p: dict, at):
	from construction_core import sitelog
	from construction_core.api import portal

	if action == "create_update":
		name = portal.create_stage_update(
			p["project"], p["stage"], p.get("text"), p.get("progress_after"), cint(p.get("internal_only"))
		)
		return {"name": name}
	if action == "attach_media":
		update = _resolve(p["update"], "Stage Update")
		f = frappe.db.get_value(
			"File",
			{"file_url": p["file_url"], "owner": frappe.session.user},
			["name", "attached_to_name"],
			as_dict=True,
		)
		if not f:
			raise Rejected(_("The photo was not uploaded"))
		if not f.attached_to_name:
			frappe.db.set_value(
				"File", f.name, {"attached_to_doctype": "Stage Update", "attached_to_name": update}
			)
		return {"name": update, **portal.attach_media(update, p["file_url"], p.get("kind") or "Photo")}
	if action == "tick":
		stage = frappe.get_doc("Project Stage", p["stage"])
		row = next((r for r in stage.checklist if r.name == p["row"]), None)
		if not row:
			raise Rejected(_("Checklist item not found"))
		changed_on = row.get("done_on")
		if at and changed_on and get_datetime(changed_on) > at and cint(row.done) != cint(p["done"]):
			raise Rejected(_("البند ده اتغيّر على السيستم بعد ما علّمته، والسيستم هو اللي اتحفظ"))
		return portal.toggle_checklist_item(p["stage"], p["row"], cint(p["done"]))
	if action == "save_daily_log":
		return {"name": sitelog.save_daily_log(p["project"], p["data"])}
	if action == "clock":
		names = sitelog.do_clock(
			p["project"],
			p["event"],
			p["workers"],
			p.get("latitude"),
			p.get("longitude"),
			p.get("accuracy_m"),
			p.get("device_info"),
			at=at,
		)
		return {"names": names}
	raise Rejected(_("Unknown action"))


@frappe.whitelist(methods=["POST"])
def apply(uuid: str, action: str, payload: dict | str, client_time: str | None = None) -> dict:
	"""Run one queued action once. Returns {"status": "done"|"rejected", "result"|"reason"}."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	if not uuid or len(uuid) > 64 or action not in ACTIONS:
		frappe.throw(_("Invalid sync item"))
	existing = _receipt(uuid)
	if existing:
		return {"status": "done", "result": json.loads(existing.result), "repeat": True}
	payload = frappe.parse_json(payload) if isinstance(payload, str) else payload
	frappe.db.savepoint("cc_sync")
	try:
		at = _client_time(client_time)
		result = _run(action, payload, at)
	except Rejected as e:
		frappe.db.rollback(save_point="cc_sync")
		frappe.clear_messages()
		return {"status": "rejected", "reason": str(e)}
	try:
		frappe.get_doc(
			{
				"doctype": "Sync Receipt",
				"client_uuid": uuid,
				"user": frappe.session.user,
				"action": action,
				"client_time": at,
				"result": json.dumps(result, default=str),
			}
		).insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		# The same item arrived twice at the same moment: undo ours, return the first result.
		frappe.db.rollback(save_point="cc_sync")
		row = _receipt(uuid)
		return {"status": "done", "result": json.loads(row.result), "repeat": True}
	return {"status": "done", "result": result}
