# Phase 18 — AI assistant and AI connect

## Goal
1. An assistant inside the platform answers questions and drafts estimates and change orders, using **only** our server-side tools and the costing engine.
2. An optional **MCP connector** lets the owner use Claude or ChatGPT with their own account on their own data, with the same permissions.

Projul equivalent: Projul AI Connect.

## Cost note
The model provider charges per use. Development uses a small monthly cap that the owner sets. Local inference (for example Ollama) is possible but needs a much bigger server, so it is not the default.

## New DocTypes

| DocType | Type | Key fields |
|---|---|---|
| `AI Settings` | single | provider, model, api_key (Password field, stored encrypted by Frappe), monthly_cap_usd, enabled |
| `AI Conversation` | normal | user, project, started_on, messages (JSON) |
| `AI Tool Log` | normal | conversation, user, tool, input_json, output_json, tokens_in, tokens_out, cost_usd, at |

## Tools (server-side; each checks the calling user's permissions)

| Tool | What it does |
|---|---|
| `get_project_summary(project)` | Progress, schedule status, open items |
| `get_rooms_and_measurements(project)` | From approved estimates and takeoffs only |
| `get_current_prices(items)` | From the price library, with source and date |
| `run_costing(lines)` | The phase 7 engine, **the only source of money figures** |
| `draft_change_order(project, lines, description)` | Creates a Draft only |
| `draft_estimate(lead_or_project, sections)` | Creates a Draft only |
| `summarize_daily_logs(project, from, to)` | Text summary |
| `explain_variance(project)` | Uses the phase 17 report data |

## Tasks

1. **Chat panel** in the desk and in the portal (engineers and admin only in v1; clients are optional later), in Arabic.
2. **Provider-neutral client** with tool calling. Each request:
   - checks the monthly cap
   - logs every tool call and its cost
   - refuses when the cap is reached
3. **Guardrails:**
   - The assistant may never state a price, quantity or total that did not come from a tool result in the same conversation. Enforce this by checking numbers in the answer against the tool outputs, and warn if they do not match.
   - It can only create **Drafts**, never approve, send, sign or pay.
4. **MCP connector (optional for the owner):**
   - Expose the same tools through an MCP server that authenticates with a Frappe API key of the user and enforces that user's permissions.
   - Either adapt `frappe-mcp-server` (MIT, single maintainer — review the code first) or write a minimal one in `construction_core/mcp/`.
   - Read-only tools by default; draft tools are opt-in.

## Acceptance criteria
- [ ] "عايز أغيّر سيراميك الريسبشن لباركيه" produces a Draft Change Order whose numbers equal `run_costing` output (test with a mocked model).
- [ ] With the cap reached, the assistant refuses and logs it (test).
- [ ] A user without access to a project gets a permission error from every tool (tests).
- [ ] The number-check guardrail flags an injected wrong total (test).
- [ ] MCP: a read-only tool works from a desktop MCP client with an engineer's key and is denied for another engineer's project (manual test, recorded).
