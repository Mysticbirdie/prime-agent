---
name: verify-bar
description: Run the project's verification bar — typecheck, build, lint, and test suite. Blocks on failure (non-zero exit). Use before shipping any change. Detects project type automatically (Node, Python, or both). Can be used as an autonomous quality gate.
---

# Verify Bar

Runs the project's full verification bar and blocks on failure. Detects the
project type automatically and runs the relevant checks.

## Usage

From IPython:

```python
# Full verification bar
result = await verify_bar()

# Fast inner loop (skip slow checks like parity gates)
result = await verify_bar(quick=True)
```

From shell:

```bash
verify_bar              # full bar
verify_bar --quick      # fast inner loop
```

As an autonomous gate:

```bash
prime-agent --autonomous --autonomous-gate "verify_bar" "Implement the change"
```

## What it checks

The bar auto-detects project type and runs the relevant stages:

### Node/TypeScript projects (package.json present)
- **Typecheck + build**: `npm run build` or `npm run build:check` if available
- **Lint**: `npm run lint` (errors block, warnings are advisory)

### Python projects (pyproject.toml / setup.py / requirements.txt present)
- **Test suite**: `python -m pytest` (or the project's configured test runner)
- Uses `.venv-test/bin/python` if present (isolated test venv), else `python3`

### Both (monorepo)
- Runs Node stages then Python stages

### Custom verification script
- If `scripts/verify_all.sh` exists, runs that instead of auto-detection

## Rules

- Blocks on failure: returns non-zero exit code if any stage fails
- Returns a structured summary: per-stage PASS/FAIL and overall status
- In `--quick` mode, skips slow stages (parity gates, full builds) and runs
  only the fast inner loop (typecheck + unit tests)
- If a stage's command is not found, reports SKIP rather than FAIL
