"""Phase 18: assistant with a mocked model — draft change order priced by the engine, monthly cap,
per-user permissions in every tool, number guardrail, drafts only, MCP dispatch."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from construction_core.ai import chat, client, guardrail, tools
from construction_core.mcp import server
from construction_core.tests.factories import make_world
from construction_core.tests.test_estimating import price

REMOVE_ADD = [
	{
		"section": "الريسبشن",
		"line_type": "Material",
		"item": "سيراميك المساعد",
		"qty": -20,
		"description": "شيل السيراميك",
	},
	{
		"section": "الريسبشن",
		"line_type": "Material",
		"item": "باركيه المساعد",
		"qty": 20,
		"description": "باركيه",
	},
]


class TestAssistant(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.w = make_world()
		day = add_days(nowdate(), -10)
		price("سيراميك المساعد", 250, day)
		price("باركيه المساعد", 600, day)
		s = frappe.get_doc("AI Settings")
		s.api_key = "test-key-not-real"
		s.monthly_cap_usd = 10
		s.input_price_per_mtok = 3
		s.output_price_per_mtok = 15
		s.max_steps = 6
		s.mcp_enabled = 1
		s.mcp_allow_drafts = 0
		s.save(ignore_permissions=True)
		frappe.db.set_single_value("Inceptiondesign Settings", "enable_ai_assistant", 1)

	def setUp(self):
		frappe.clear_document_cache("AI Settings")
		frappe.db.delete("AI Tool Log")

	def scripted(self, *turns):
		it = iter(turns)
		return patch.object(client, "complete", side_effect=lambda messages, specs: next(it))

	def test_ceramic_to_parquet_draft_matches_engine(self):
		project = self.w.p1
		costing = None

		def turns():
			nonlocal costing
			yield client.Turn(
				tool_calls=[{"id": "t1", "name": "run_costing", "input": {"lines": REMOVE_ADD}}],
				tokens_in=900,
				tokens_out=80,
			)
			yield client.Turn(
				tool_calls=[
					{
						"id": "t2",
						"name": "draft_change_order",
						"input": {
							"project": project,
							"lines": REMOVE_ADD,
							"description": "تغيير سيراميك الريسبشن لباركيه",
						},
					}
				],
				tokens_in=1200,
				tokens_out=90,
			)
			total = frappe.get_all(
				"Change Order",
				filters={"project": project},
				fields=["cost_difference"],
				order_by="creation desc",
				limit=1,
			)[0].cost_difference
			yield client.Turn(
				text=f"عملت مسودة أمر تغيير، الفرق {total:,.2f} جنيه.", tokens_in=1400, tokens_out=60
			)

		gen = turns()
		with (
			patch.object(client, "complete", side_effect=lambda m, s: next(gen)),
			self.set_user(self.w.users.eng1),
		):
			costing = tools.run_costing(REMOVE_ADD)
			res = chat.send("عايز أغيّر سيراميك الريسبشن لباركيه", project=project)
		self.assertEqual(res["warnings"], [], res["reply"])
		self.assertEqual(len(res["drafts"]), 1)
		co = frappe.get_doc("Change Order", res["drafts"][0]["name"])
		self.assertEqual(co.status, "Draft")
		self.assertEqual(co.docstatus, 0)
		self.assertEqual(f"{co.cost_difference:.2f}", costing["total"])
		self.assertEqual(costing["total"], "7000.00")  # (600 − 250) × 20
		logs = frappe.get_all("AI Tool Log", filters={"conversation": res["conversation"]}, pluck="tool")
		self.assertIn("run_costing", logs)
		self.assertIn("draft_change_order", logs)
		self.assertGreater(client.month_spend(), 0)

	def test_cap_reached_refuses_and_logs(self):
		frappe.db.set_single_value("AI Settings", "monthly_cap_usd", 0.01)
		frappe.clear_document_cache("AI Settings")
		client.log(None, "model", True, tokens_in=1, tokens_out=1, cost=0.02)
		with patch.object(client, "complete") as model, self.set_user(self.w.users.eng1):
			res = chat.send("ازيك")
		model.assert_not_called()
		self.assertTrue(res["refused"])
		self.assertTrue(frappe.db.exists("AI Tool Log", {"tool": "cap_refused"}))
		frappe.db.set_single_value("AI Settings", "monthly_cap_usd", 10)

	def test_every_tool_denies_other_projects(self):
		p1 = self.w.p1
		calls = {
			"get_project_summary": {"project": p1},
			"get_rooms_and_measurements": {"project": p1},
			"summarize_daily_logs": {"project": p1},
			"explain_variance": {"project": p1},
			"draft_change_order": {"project": p1, "lines": REMOVE_ADD, "description": "x"},
			"draft_estimate": {"project": p1, "sections": [{"section": "x", "lines": REMOVE_ADD}]},
		}
		with self.set_user(self.w.users.eng2):
			for name, args in calls.items():
				self.assertRaises(frappe.PermissionError, tools.call_tool, name, args)
		with self.set_user(self.w.users.client1):
			for name in ("run_costing", "get_current_prices"):
				self.assertRaises(
					frappe.PermissionError,
					tools.call_tool,
					name,
					{"lines": REMOVE_ADD} if name == "run_costing" else {"items": ["x"]},
				)
			self.assertRaises(frappe.PermissionError, chat.send, "سؤال")

	def test_guardrail_flags_invented_total(self):
		outputs = [{"total": "7000.00", "lines": [{"qty": -20, "line_total": "-5000.00"}]}]
		self.assertEqual(guardrail.unsupported_numbers("الإجمالي 7,000 جنيه و20 متر", outputs), [])
		self.assertEqual(guardrail.unsupported_numbers("الإجمالي ١٢٥٠٠ جنيه", outputs), [12500])
		with (
			self.scripted(
				client.Turn(tool_calls=[{"id": "a", "name": "run_costing", "input": {"lines": REMOVE_ADD}}]),
				client.Turn(text="التكلفة 9,999 جنيه"),
			),
			self.set_user(self.w.users.eng1),
		):
			res = chat.send("كام؟")
		self.assertTrue(res["warnings"])
		self.assertIn("9999", res["warnings"][0])
		self.assertTrue(frappe.db.exists("AI Tool Log", {"tool": "guardrail_flag"}))

	def test_only_drafts(self):
		self.assertNotIn("send_to_client", tools.READ_ONLY | tools.DRAFTS)
		with self.set_user(self.w.users.eng1):
			self.assertRaises(
				frappe.ValidationError, tools.call_tool, "engineer_approve", {"change_order": "x"}
			)
			out = tools.draft_change_order(self.w.p1, REMOVE_ADD, "تجربة")
		self.assertEqual(frappe.db.get_value("Change Order", out["change_order"], "status"), "Draft")
		# prices typed by the model are ignored
		with self.set_user(self.w.users.eng1):
			out = tools.run_costing(
				[{"line_type": "Other", "description": "مصنعية", "qty": 1, "unit_cost": 99999}]
			)
		self.assertEqual(out["total"], "0.00")


class TestMcp(IntegrationTestCase):
	def test_read_only_tool_scoped_by_user(self):
		w = make_world()
		frappe.db.set_single_value("AI Settings", "mcp_allow_drafts", 0)
		frappe.clear_document_cache("AI Settings")
		with self.set_user(w.users.eng1):
			listed = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
			names = [t["name"] for t in listed["result"]["tools"]]
			self.assertIn("get_project_summary", names)
			self.assertNotIn("draft_change_order", names)
			ok = server.dispatch(
				{
					"jsonrpc": "2.0",
					"id": 2,
					"method": "tools/call",
					"params": {"name": "get_project_summary", "arguments": {"project": w.p1}},
				}
			)
			self.assertFalse(ok["result"]["isError"])
			denied = server.dispatch(
				{
					"jsonrpc": "2.0",
					"id": 3,
					"method": "tools/call",
					"params": {"name": "get_project_summary", "arguments": {"project": w.p2}},
				}
			)
			self.assertTrue(denied["result"]["isError"])
			self.assertIn("permission", denied["result"]["content"][0]["text"])
			drafted = server.dispatch(
				{
					"jsonrpc": "2.0",
					"id": 4,
					"method": "tools/call",
					"params": {
						"name": "draft_change_order",
						"arguments": {"project": w.p1, "lines": REMOVE_ADD, "description": "x"},
					},
				}
			)
			self.assertTrue(drafted["result"]["isError"])
			init = server.dispatch({"jsonrpc": "2.0", "id": 5, "method": "initialize", "params": {}})
			self.assertEqual(init["result"]["serverInfo"]["name"], "inceptiondesign")
