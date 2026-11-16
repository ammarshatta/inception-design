# Phase 18 stories

## P18-01 · AI assistant · Should

**Role:** Engineer  
**Story:** As an engineer, I want to ask the assistant in Arabic to draft a change order, so that pricing a change takes seconds.

**Acceptance criteria**

1. Given "عايز أغيّر سيراميك الريسبشن لباركيه" on my project, when I send it, then a Draft change order is created whose numbers equal the costing engine's output.

## P18-02 · AI assistant · Must

**Role:** Owner  
**Story:** As an owner, I want a monthly AI spending cap, so that costs never surprise me.

**Acceptance criteria**

1. Given the monthly cap is reached, when anyone asks the assistant, then it refuses politely and the refusal is logged.

## P18-03 · AI assistant · Must

**Role:** Owner  
**Story:** As an owner, I want the assistant limited to each user's permissions and to drafts, so that AI cannot leak data or approve money.

**Acceptance criteria**

1. Given a user without access to a project, when they ask about it, then every tool returns a permission error.
2. Given any conversation, when the assistant is asked to approve, send, sign or pay, then it can only create drafts.

## P18-04 · AI assistant · Must

**Role:** Owner  
**Story:** As an owner, I want a check that every number the AI states comes from a tool, so that no invented prices reach anyone.

**Acceptance criteria**

1. Given an answer containing a total that no tool returned, when the guardrail runs, then the answer is flagged and the user warned.

## P18-05 · AI assistant · Could

**Role:** Owner  
**Story:** As an owner, I want to use Claude or ChatGPT with my data through an MCP connector, so that I work from the AI tools I already use.

**Acceptance criteria**

1. Given an MCP client configured with an engineer's API key, when it calls a read-only tool for their project, then data is returned; for another engineer's project it is denied.
