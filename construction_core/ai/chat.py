"""Chat endpoint for the assistant panel (phase 18). Engineers and the office only."""

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from construction_core.ai import client, guardrail, tools
from construction_core.permissions import assert_project_access, is_client

ALLOWED_ROLES = {"Construction Engineer", "Construction Admin", "Construction Sales", "System Manager"}


def _require_user():
	if frappe.session.user == "Guest" or is_client() or not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw(_("المساعد متاح للمهندسين والمكتب بس"), frappe.PermissionError)
	if not frappe.db.get_single_value("Inceptiondesign Settings", "enable_ai_assistant"):
		frappe.throw(_("المساعد مقفول من الإعدادات"))
	if not client.settings().get_password("api_key", raise_exception=False):
		frappe.throw(_("المساعد لسه ماتظبطش (مفيش مفتاح)"))


def _conversation(name: str | None, project: str | None):
	if name:
		conv = frappe.get_doc("AI Conversation", name)
		if conv.user != frappe.session.user:
			frappe.throw(_("Not found"), frappe.PermissionError)
		return conv
	if project:
		assert_project_access(project)
	conv = frappe.get_doc(
		{
			"doctype": "AI Conversation",
			"user": frappe.session.user,
			"project": project,
			"started_on": now_datetime(),
			"messages": "[]",
		}
	)
	conv.insert(ignore_permissions=True)
	return conv


@frappe.whitelist(methods=["POST"])
def send(message: str, conversation: str | None = None, project: str | None = None) -> dict:
	_require_user()
	message = (message or "").strip()[:4000]
	if not message:
		frappe.throw(_("اكتب سؤالك"))
	conv = _conversation(conversation, project)
	history = json.loads(conv.messages or "[]")
	prefix = f"[المشروع: {conv.project}] " if conv.project and not history else ""
	history.append({"role": "user", "content": prefix + message})
	try:
		client.check_cap(conv.name)
	except client.CapReached as e:
		return {"conversation": conv.name, "reply": str(e), "refused": True, "warnings": [], "drafts": []}

	specs = tools.tool_specs(include_drafts=True)
	outputs, drafts = [], []
	steps = cint(client.settings().max_steps) or 6
	reply = ""
	for _step in range(steps):
		client.check_cap(conv.name)
		turn = client.complete(history, specs)
		client.log(
			conv.name,
			"model",
			True,
			tokens_in=turn.tokens_in,
			tokens_out=turn.tokens_out,
			cost=client.cost_of(turn),
		)
		content = []
		if turn.text:
			content.append({"type": "text", "text": turn.text})
		for call in turn.tool_calls:
			content.append(
				{"type": "tool_use", "id": call["id"], "name": call["name"], "input": call["input"]}
			)
		history.append({"role": "assistant", "content": content})
		if not turn.tool_calls:
			reply = turn.text
			break
		results = []
		for call in turn.tool_calls:
			try:
				out = tools.call_tool(call["name"], call["input"])
				ok = True
				outputs.append(out)
				if isinstance(out, dict) and (out.get("change_order") or out.get("estimate")):
					drafts.append(
						{
							"doctype": "Change Order" if out.get("change_order") else "Estimate",
							"name": out.get("change_order") or out.get("estimate"),
						}
					)
			except frappe.PermissionError:
				frappe.clear_messages()
				out, ok = {"error": "permission denied"}, False
			except Exception as e:
				frappe.clear_messages()
				out, ok = {"error": str(e)[:300]}, False
			client.log(conv.name, call["name"], ok, call["input"], out)
			results.append(
				{
					"type": "tool_result",
					"tool_use_id": call["id"],
					"content": json.dumps(out, ensure_ascii=False, default=str),
				}
			)
		history.append({"role": "user", "content": results})
	else:
		reply = _("وقفت علشان الخطوات كترت. جرّب تسأل بشكل أبسط.")

	flagged = guardrail.unsupported_numbers(reply, outputs)
	warnings = []
	if flagged:
		warnings.append(
			_("تنبيه: الأرقام دي ما طلعتش من أدوات السيستم، متعتمدش عليها: {0}").format(
				"، ".join(f"{n:g}" for n in flagged)
			)
		)
		client.log(conv.name, "guardrail_flag", False, {"reply": reply}, {"numbers": flagged})
	conv.messages = json.dumps(history, ensure_ascii=False)
	if not conv.title:
		conv.title = message[:80]
	conv.save(ignore_permissions=True)
	return {
		"conversation": conv.name,
		"reply": reply,
		"warnings": warnings,
		"drafts": drafts,
		"refused": False,
	}
