"""Minimal MCP server (JSON-RPC 2.0 over HTTP POST), phase 18.

Endpoint: POST /api/method/construction_core.mcp.server.handle
Auth: the user's Frappe API key ("Authorization: token <key>:<secret>"); Frappe sets the session
user, and every tool checks that user's permissions. Read-only tools by default; draft tools
only when "السماح بأدوات إنشاء المسودات عبر MCP" is on in AI Settings.
Implements: initialize, notifications/initialized, ping, tools/list, tools/call.
"""

import json

import frappe
from werkzeug.wrappers import Response

from construction_core.ai import tools

PROTOCOL = "2025-06-18"


def _reply(id_, result=None, error=None):
	body = {"jsonrpc": "2.0", "id": id_}
	if error:
		body["error"] = error
	else:
		body["result"] = result
	return body


def dispatch(req: dict) -> dict | None:
	method, id_, params = req.get("method"), req.get("id"), req.get("params") or {}
	s = frappe.get_cached_doc("AI Settings")
	drafts = bool(s.mcp_allow_drafts)
	if method == "initialize":
		return _reply(
			id_,
			{
				"protocolVersion": PROTOCOL,
				"capabilities": {"tools": {}},
				"serverInfo": {"name": "inceptiondesign", "version": "1.0"},
			},
		)
	if method and method.startswith("notifications/"):
		return None
	if method == "ping":
		return _reply(id_, {})
	if method == "tools/list":
		return _reply(
			id_,
			{
				"tools": [
					{"name": t["name"], "description": t["description"], "inputSchema": t["input_schema"]}
					for t in tools.tool_specs(include_drafts=drafts)
				]
			},
		)
	if method == "tools/call":
		name = params.get("name")
		try:
			out = tools.call_tool(name, params.get("arguments") or {}, include_drafts=drafts)
			return _reply(
				id_,
				{
					"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, default=str)}],
					"isError": False,
				},
			)
		except frappe.PermissionError:
			frappe.clear_messages()
			return _reply(id_, {"content": [{"type": "text", "text": "permission denied"}], "isError": True})
		except Exception as e:
			frappe.clear_messages()
			return _reply(id_, {"content": [{"type": "text", "text": str(e)[:300]}], "isError": True})
	return _reply(id_, error={"code": -32601, "message": "Method not found"})


@frappe.whitelist(methods=["POST"])
def handle():
	if frappe.session.user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	if not frappe.db.get_single_value("AI Settings", "mcp_enabled"):
		frappe.throw("MCP is turned off", frappe.PermissionError)
	payload = json.loads(frappe.request.get_data(as_text=True) or "{}")
	if isinstance(payload, list):
		out = [r for r in (dispatch(p) for p in payload) if r is not None]
	else:
		out = dispatch(payload)
	if out is None or out == []:
		return Response(status=202)
	return Response(json.dumps(out, ensure_ascii=False, default=str), content_type="application/json")
