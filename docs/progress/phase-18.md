# Phase 18 — AI assistant and AI connect (MCP)

**Status:** ✅ Unit tests (166) and Playwright tests green in CI run 43977742055 (17 Nov 2026).

**Approval:** built without waiting between phases, as the owner asked on 16 Nov 2026. CI is the gate. Nothing paid was turned on: the tests use a mocked model.

## Cost (owner decision)

The model provider charges per use (per million tokens in and out). The prices are **fields in AI Settings**, not in code, so the cost log follows whatever the owner's plan charges. A monthly cap in dollars stops the assistant when reached (the default cap is 10 USD; the assistant stays off until a key is entered and "المساعد الذكي" is on in Inceptiondesign Settings).

## What was built

| Task | Where |
|---|---|
| **AI Settings** (single): provider (Anthropic or any OpenAI-compatible API), model, API base, key (Password, encrypted), monthly cap, prices per million tokens, max tool steps, MCP switches | `doctype/ai_settings` |
| **AI Conversation** and **AI Tool Log** (every model call and tool call with input, output, tokens, cost) | `doctype/ai_conversation`, `doctype/ai_tool_log` |
| Tools, each running as the user and checking access: `get_project_summary`, `get_rooms_and_measurements`, `get_current_prices`, `run_costing` (the phase 7 engine — the only source of money), `draft_change_order`, `draft_estimate`, `summarize_daily_logs`, `explain_variance` (phase 17 data) | `ai/tools.py` |
| Prices typed by the model are **dropped**: the engine looks every price up (an "Other" line starts at 0 for a person to fill) | `tools._clean_lines` |
| Provider-neutral client with tool calling (plain HTTPS, no SDK), the cap checked before every model call, cost logged | `ai/client.py` |
| **Number guardrail**: every number ≥ 10 in the answer (Western or Arabic digits, with or without thousands separators) must appear in a tool output of the same conversation; otherwise the user sees a warning and it is logged | `ai/guardrail.py` |
| Drafts only: there is no tool that approves, sends, signs or pays; the system prompt also refuses | `ai/tools.py`, `ai/client.SYSTEM` |
| Chat panel in the portal for engineers and the office (`/portal/assistant`), links to the created drafts | `ai/chat.py`, `AssistantPage.vue` |
| **MCP connector**: minimal JSON-RPC MCP server at `/api/method/construction_core.mcp.server.handle`, authenticated with the user's Frappe API key, same tools and permissions; read-only unless "السماح بأدوات إنشاء المسودات" is on | `mcp/server.py` |

We wrote a minimal MCP server (about 100 lines) instead of adapting `frappe-mcp-server`, so there is no outside code to review or keep updated.

## Not done

- A desk (`/app`) chat panel: office users use the portal page.
- Streaming answers (the reply arrives in one piece).

## Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| "عايز أغيّر سيراميك الريسبشن لباركيه" → Draft Change Order whose numbers equal `run_costing` (mocked model) | `test_ai.test_ceramic_to_parquet_draft_matches_engine` (7,000.00 = (600 − 250) × 20) | ✅ CI |
| Cap reached → refuses and logs | `test_cap_reached_refuses_and_logs` | ✅ CI |
| A user without access gets a permission error from every tool | `test_every_tool_denies_other_projects` | ✅ CI |
| Guardrail flags an injected wrong total | `test_guardrail_flags_invented_total` | ✅ CI |
| Drafts only | `test_only_drafts` | ✅ CI |
| MCP: read-only tool works with an engineer's key and is denied for another engineer's project | `TestMcp` (dispatch as the user); desktop client test needs the owner | ✅ CI · ☐ (owner) |
