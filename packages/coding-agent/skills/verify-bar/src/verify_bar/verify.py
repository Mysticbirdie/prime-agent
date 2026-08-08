"""Verify bar — runs the project's full verification suite.

Auto-detects project type (Node, Python, or both) and runs the relevant
checks. Blocks on failure. If a custom scripts/verify_all.sh exists, uses
that instead.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StageResult:
    name: str
    status: str  # PASS, FAIL, SKIP
    output: str = ""


@dataclass
class VerifyResult:
    stages: list[StageResult] = field(default_factory=list)
    failures: int = 0

    @property
    def passed(self) -> bool:
        return self.failures == 0

    def __str__(self) -> str:
        lines = ["", "=" * 66, "Verify Bar Summary", "=" * 66]
        for stage in self.stages:
            marker = "PASS" if stage.status == "PASS" else stage.status
            lines.append(f"  {marker:4s}  {stage.name}")
        lines.append("-" * 66)
        if self.passed:
            lines.append("ALL GREEN — verification bar met.")
        else:
            lines.append(f"{self.failures} stage(s) FAILED — verification bar NOT met.")
        return "\n".join(lines)


async def _run_command(cmd: list[str], cwd: Path, timeout: int = 300) -> StageResult:
    """Run a command and return its result."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            status = "PASS" if proc.returncode == 0 else "FAIL"
            return StageResult(name=" ".join(cmd[:2]), status=status, output=output)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return StageResult(name=" ".join(cmd[:2]), status="FAIL", output="TIMEOUT")
    except FileNotFoundError:
        return StageResult(name=" ".join(cmd[:2]), status="SKIP", output="command not found")


def _has_node(root: Path) -> bool:
    return (root / "package.json").exists()


def _has_python(root: Path) -> bool:
    return any(
        (root / f).exists()
        for f in ("pyproject.toml", "setup.py", "requirements.txt", "setup.cfg")
    )


def _has_custom_script(root: Path) -> bool:
    return (root / "scripts" / "verify_all.sh").exists()


def _find_python(root: Path) -> str:
    """Find the Python executable to use for tests."""
    venv_test = root / ".venv-test" / "bin" / "python"
    if venv_test.exists():
        return str(venv_test)
    return shutil.which("python3") or "python3"


async def _run_custom_script(root: Path, quick: bool) -> list[StageResult]:
    cmd = ["bash", "scripts/verify_all.sh"]
    if quick:
        cmd.append("--quick")
    result = await _run_command(cmd, root, timeout=600)
    return [result]


async def _run_node_stages(root: Path, quick: bool) -> list[StageResult]:
    results: list[StageResult] = []
    frontend = root / "frontend"

    # If there's a frontend/ subdir with its own package.json, use that
    node_root = frontend if frontend.exists() and (frontend / "package.json").exists() else root

    # Typecheck + build
    build_cmd = None
    if (node_root / "package.json").exists():
        import json
        try:
            pkg = json.loads((node_root / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if "build:check" in scripts:
                build_cmd = ["npm", "run", "build:check"]
            elif "build" in scripts:
                build_cmd = ["npm", "run", "build"]
        except (ValueError, OSError):
            pass

    if build_cmd:
        result = await _run_command(build_cmd, node_root, timeout=300)
        result.name = "Node (typecheck + build)"
        results.append(result)

    # Lint (errors only, warnings advisory)
    if not quick:
        lint_cmd = None
        if (node_root / "package.json").exists():
            import json
            try:
                pkg = json.loads((node_root / "package.json").read_text())
                scripts = pkg.get("scripts", {})
                if "lint" in scripts:
                    lint_cmd = ["npm", "run", "lint"]
            except (ValueError, OSError):
                pass

        if lint_cmd:
            result = await _run_command(lint_cmd, node_root, timeout=120)
            result.name = "Node (lint)"
            results.append(result)

    return results


async def _run_python_stages(root: Path, quick: bool) -> list[StageResult]:
    results: list[StageResult] = []
    py = _find_python(root)

    # Pytest
    test_cmd = [py, "-m", "pytest", "-q"]
    if quick:
        test_cmd.extend(["-x", "--tb=short"])

    # Check if functions/ dir exists (Birdhouse-style) or tests/ dir
    test_target = "functions/" if (root / "functions").exists() else ""
    cmd = test_cmd + ([test_target] if test_target else [])
    result = await _run_command(cmd, root, timeout=300)
    result.name = "Python (pytest)"
    results.append(result)

    return results


async def run(quick: bool = False) -> str:
    """Run the project's verification bar.

    Args:
        quick: Fast inner loop — skip slow stages (parity gates, full builds),
            run only typecheck + unit tests.

    Returns:
        Formatted verification report. Non-zero failures indicate the bar
        was not met.
    """
    root = Path.cwd()
    results: list[StageResult] = []

    # Custom script takes precedence
    if _has_custom_script(root):
        results = await _run_custom_script(root, quick)
    else:
        if _has_node(root):
            results.extend(await _run_node_stages(root, quick))
        if _has_python(root):
            results.extend(await _run_python_stages(root, quick))
        if not results:
            return "[SKIP] No recognizable project type (no package.json, pyproject.toml, or scripts/verify_all.sh)"

    failures = sum(1 for r in results if r.status == "FAIL")
    verify = VerifyResult(stages=results, failures=failures)

    output_lines = [str(verify)]

    # Include failed stage output for debugging
    failed = [r for r in results if r.status == "FAIL" and r.output]
    if failed:
        output_lines.append("")
        output_lines.append("Failed stage output:")
        for stage in failed:
            output_lines.append(f"\n--- {stage.name} ---")
            # Truncate long output
            out = stage.output
            if len(out) > 2000:
                out = out[:2000] + "\n... (truncated)"
            output_lines.append(out)

    return "\n".join(output_lines)
