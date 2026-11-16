"""Provider-neutral model client with tool calling, a monthly cap and a cost log (phase 18).

The model is only a planner: it may call the tools in `ai.tools`, which run as the user. The
number check runs on every final answer. Keys: AI Settings (Password, encrypted). No SDK is
needed: plain HTTPS calls.
"""

import json
from dataclasses import dataclass, field

import frappe
import requests
from frappe import _
from frappe.utils import flt, get_first_day, now_datetime, nowdate

TIMEOUT = 60

SYSTEM = (
	"أنت مساعد مكتب مقاولات وتشطيبات في مصر. اتكلم بالعامية المصرية وباختصار. "
	"ممنوع تذكر أي سعر أو كمية أو إجمالي ما طلعش من أداة في نفس المحادثة؛ للأسعار استخدم run_costing أو أدوات المسودات. "
	"تقدر تعمل مسودات بس (أمر تغيير أو تسعير). ممنوع تعتمد أو تبعت أو توقّع أو تدفع أي حاجة؛ لو اتطلب منك ده قول إن ده بيتعمل من المكتب. "
	"لما تعمل مسودة اذكر رقمها. الإزالة في أمر التغيير كمية بالسالب."
)


@dataclass
class Turn:
	text: str = ""
	tool_calls: list = field(default_factory=list)  # [{"id", "name", "input"}]
	tokens_in: int = 0
	tokens_out: int = 0


class CapReached(frappe.ValidationError):
	pass


def settings():
	return frappe.get_cached_doc("AI Settings")


def month_spend() -> float:
	return flt(
		frappe.db.sql(
			"select ifnull(sum(cost_usd), 0) from `tabAI Tool Log` where at >= %s", get_first_day(nowdate())
		)[0][0],
		6,
	)


def log(conversation, tool, ok, input_=None, output=None, tokens_in=0, tokens_out=0, cost=0.0):
	frappe.get_doc(
		{
			"doctype": "AI Tool Log",
			"conversation": conversation,
			"user": frappe.session.user,
			"tool": tool,
			"ok": 1 if ok else 0,
			"input_json": json.dumps(input_, ensure_ascii=False, default=str)[:20000]
			if input_ is not None
			else None,
			"output_json": json.dumps(output, ensure_ascii=False, default=str)[:20000]
			if output is not None
			else None,
			"tokens_in": tokens_in,
			"tokens_out": tokens_out,
			"cost_usd": cost,
			"at": now_datetime(),
		}
	).insert(ignore_permissions=True)


def check_cap(conversation):
	s = settings()
	cap = flt(s.monthly_cap_usd)
	if cap <= 0 or month_spend() >= cap:
		log(conversation, "cap_refused", False, output={"spent": month_spend(), "cap": cap})
		raise CapReached(_("وصلنا لسقف المساعد الشهري. كلّم المكتب يزوّده أو استنى الشهر الجاي."))


def cost_of(turn: Turn) -> float:
	s = settings()
	return flt(
		turn.tokens_in * flt(s.input_price_per_mtok) / 1e6
		+ turn.tokens_out * flt(s.output_price_per_mtok) / 1e6,
		6,
	)


# --- Providers ------------------------------------------------------------------------


def _anthropic(messages, tools) -> Turn:
	s = settings()
	r = requests.post(
		f"{(s.api_base or 'https://api.anthropic.com').rstrip('/')}/v1/messages",
		headers={
			"x-api-key": s.get_password("api_key"),
			"anthropic-version": "2023-06-01",
			"content-type": "application/json",
		},
		json={"model": s.model, "max_tokens": 1500, "system": SYSTEM, "messages": messages, "tools": tools},
		timeout=TIMEOUT,
	)
	if r.status_code >= 300:
		frappe.log_error(title="AI provider error", message=r.text[:2000])
		frappe.throw(_("المساعد مش متاح دلوقتي"))
	data = r.json()
	turn = Turn(
		tokens_in=data.get("usage", {}).get("input_tokens", 0),
		tokens_out=data.get("usage", {}).get("output_tokens", 0),
	)
	for block in data.get("content", []):
		if block.get("type") == "text":
			turn.text += block["text"]
		elif block.get("type") == "tool_use":
			turn.tool_calls.append(
				{"id": block["id"], "name": block["name"], "input": block.get("input") or {}}
			)
	return turn


def _openai(messages, tools) -> Turn:
	s = settings()
	oa_messages = [{"role": "system", "content": SYSTEM}]
	for m in messages:
		if isinstance(m["content"], str):
			oa_messages.append(m)
			continue
		for block in m["content"]:
			if block["type"] == "text":
				oa_messages.append({"role": m["role"], "content": block["text"]})
			elif block["type"] == "tool_use":
				oa_messages.append(
					{
						"role": "assistant",
						"tool_calls": [
							{
								"id": block["id"],
								"type": "function",
								"function": {"name": block["name"], "arguments": json.dumps(block["input"])},
							}
						],
					}
				)
			elif block["type"] == "tool_result":
				oa_messages.append(
					{"role": "tool", "tool_call_id": block["tool_use_id"], "content": block["content"]}
				)
	r = requests.post(
		f"{(s.api_base or '').rstrip('/')}/v1/chat/completions",
		headers={"Authorization": f"Bearer {s.get_password('api_key')}"},
		json={
			"model": s.model,
			"messages": oa_messages,
			"tools": [
				{
					"type": "function",
					"function": {
						"name": t["name"],
						"description": t["description"],
						"parameters": t["input_schema"],
					},
				}
				for t in tools
			],
		},
		timeout=TIMEOUT,
	)
	if r.status_code >= 300:
		frappe.log_error(title="AI provider error", message=r.text[:2000])
		frappe.throw(_("المساعد مش متاح دلوقتي"))
	data = r.json()
	msg = data["choices"][0]["message"]
	turn = Turn(
		text=msg.get("content") or "",
		tokens_in=data.get("usage", {}).get("prompt_tokens", 0),
		tokens_out=data.get("usage", {}).get("completion_tokens", 0),
	)
	for c in msg.get("tool_calls") or []:
		turn.tool_calls.append(
			{
				"id": c["id"],
				"name": c["function"]["name"],
				"input": json.loads(c["function"]["arguments"] or "{}"),
			}
		)
	return turn


def complete(messages, tools) -> Turn:
	"""One model call. Tests replace this function."""
	if (settings().provider or "Anthropic") == "Anthropic":
		return _anthropic(messages, tools)
	return _openai(messages, tools)
