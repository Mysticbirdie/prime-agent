---
name: devtrail-bridge
description: Bridge DevTrail cross-tool memory into prime-agent's continual harness. Use at session start to load prior context (project brain, recent sessions, active decisions) and at session end to capture decisions back. Requires DevTrail MCP server to be connected via /login > MCP Connections.
---

# DevTrail Bridge

DevTrail is a cross-tool memory layer that records sessions, decisions, and
patterns across coding tools. This skill bridges DevTrail memories into
prime-agent's continual harness so context persists across tools, not just
within prime-agent.

## Prerequisites

DevTrail must be connected as an MCP server. If not configured:

1. Run `/login`
2. Switch to **MCP Connections**
3. Add the DevTrail MCP server
4. Restart the session

## At session start

Load prior context before starting non-trivial work. Call these MCP tools in
order:

1. **`devtrail_project_brain`** — repo architecture docs, decision log, open
   threads. This gives you the project's structural understanding.
2. **`devtrail_recent`** (days: 7) — what happened recently across all tools.
   Catches you up on work done outside prime-agent.
3. **`devtrail_decisions`** — active architectural/implementation decisions.
   Flag any that conflict with the planned approach before proceeding.
4. **`devtrail_search "<topic>"`** — search for anything touching the area
   you're about to change (e.g. "stella recall", "auth flow", "hosting
   rewrites").

Synthesize what's relevant to the current task — do not dump everything into
context. If a search surfaces a prior decision that conflicts with the planned
approach, flag it to the user before proceeding.

## Bridging into the continual harness

After loading DevTrail context, promote durable lessons into the harness via
`/refine`:

```python
await refine.run("create a memory from DevTrail: <key finding>")
```

This makes cross-tool knowledge available to prime-agent's auto-refine system,
not just the current session's context window.

## At session end

Capture the session back to DevTrail so other tools can see it:

1. Call **`devtrail_capture_session`** with:
   - A one-line summary of what was done
   - Tags relevant to the work (e.g. "stella", "voice", "frontend")
   - Files touched
2. If a significant decision was made, also call **`devtrail_capture_session`**
   with the decision rationale and alternatives considered.

## When to use

- **Always at session start** for non-trivial work (multi-file changes, new
  features, bug fixes that touch behavior)
- **Always at session end** if anything meaningful was done
- **Mid-session** when you hit a decision point that future sessions should
  know about

## When to skip

- Trivial edits (typo, comment, copy tweak)
- Read-only exploration with no decisions made
- Sessions where nothing was changed or decided

## Conflict resolution

If DevTrail records a decision that conflicts with what the user is asking
you to do now:
1. Surface the conflict to the user explicitly
2. Do not silently override the prior decision
3. If the user confirms the override, capture the new decision to DevTrail
   with a note about what it supersedes and why
