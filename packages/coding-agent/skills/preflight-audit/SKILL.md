---
name: preflight-audit
description: Fast regex-based code audit for common AI-generated issues — invented imports, security patterns (eval/exec/shell=True/hardcoded secrets), sycophantic tests (low assertion density, missing negative cases), and token waste (verbose names, redundant comments, dead scaffolding). Use before commits or when reviewing AI-generated code. Advisory only, never blocks.
---

# Preflight Audit

Quick heuristic check (<1s) via the `preflight_audit` Python skill. Always
advisory — never blocks commits. If it flags real issues on a significant
change, escalate to the `impact-map` skill for a full adversarial review.

## Usage

From IPython:

```python
# Audit staged git changes
result = await preflight_audit()

# Audit a specific file
result = await preflight_audit("src/auth.py")

# Audit a specific file with verbose output
result = await preflight_audit("src/auth.py", verbose=True)
```

From shell:

```bash
preflight_audit                          # staged changes
preflight_audit src/auth.py              # specific file
preflight_audit --verbose                # verbose output
```

## What it checks

1. **Invented imports** — verifies that internal/relative imports resolve to
   actual files. Flags imports that look like project modules but don't exist.
   This catches the LLM hallucinating a library or function.
2. **Security patterns** — `eval()`, `exec()`, `subprocess(..., shell=True)`,
   hardcoded passwords/secrets/API keys.
3. **Sycophantic tests** — low assertion density (fewer assertions than test
   functions), missing negative/edge-case tests.
4. **Token waste** — very long variable names (>30 chars), redundant comments
   that restate the obvious, large commented-out code blocks.

## Rules

- Always exits 0 / returns a report — advisory only, never blocks.
- Returns a structured result: file, status (OK/WARNINGS), and a list of
  issues with severity, type, message, and line number.
- If it flags real issues on a significant change, escalate to `impact-map`.
