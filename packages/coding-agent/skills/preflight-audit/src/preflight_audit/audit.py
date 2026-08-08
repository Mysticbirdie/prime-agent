"""Preflight audit — fast regex-based code review.

Advisory only, never blocks. Catches common AI-generated code issues:
- Invented imports (modules that don't exist in the project)
- Security patterns (eval, exec, shell=True, hardcoded secrets)
- Sycophantic tests (low assertion density, missing negative cases)
- Token waste (verbose names, redundant comments, dead scaffolding)
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AuditIssue:
    severity: str
    type: str
    message: str
    line: Optional[int] = None


@dataclass
class AuditResult:
    file: str
    status: str  # OK or WARNINGS
    issues: list[AuditIssue] = field(default_factory=list)

    def __str__(self) -> str:
        emoji = "OK" if self.status == "OK" else "WARNINGS"
        lines = [f"[{emoji}] {self.file}"]
        for issue in self.issues:
            sev = issue.severity.upper()
            ln = f":{issue.line}" if issue.line else ""
            lines.append(f"  [{sev}]{ln} {issue.message}")
        return "\n".join(lines)


# Standard library and common third-party packages — skip import verification
_KNOWN_PACKAGES = frozenset({
    "os", "sys", "re", "json", "pathlib", "typing", "subprocess",
    "dataclasses", "datetime", "collections", "itertools", "math",
    "random", "hashlib", "base64", "logging", "unittest", "pytest",
    "requests", "httpx", "flask", "fastapi", "django", "numpy",
    "pandas", "torch", "tensorflow", "anthropic", "openai", "asyncio",
    "functools", "contextlib", "io", "csv", "os.path", "shutil",
    "tempfile", "argparse", "configparser", "textwrap", "string",
    "enum", "abc", "copy", "pickle", "struct", "socket", "threading",
    "queue", "uuid", "time", "traceback", "warnings", "weakref",
    "inspect", "importlib", "pkgutil", "platform", "glob", "fnmatch",
    "operator", "heapq", "bisect", "array", "decimal", "fractions",
    "statistics", "secrets", "sqlite3", "xml", "html", "email",
    "urllib", "http", "ftplib", "smtplib", "ssl", "zlib", "gzip",
    "tarfile", "zipfile", "concurrent", "multiprocessing",
})


class PreflightAuditor:
    """Fast heuristic checks — advisory only, not blocking."""

    def __init__(self, codebase_root: str = "."):
        self.root = Path(codebase_root).resolve()

    def audit(self, filepath: str, content: str) -> AuditResult:
        issues: list[AuditIssue] = []
        file_path = Path(filepath)
        file_dir = file_path.parent.resolve()

        self._check_invented_imports(filepath, content, file_dir, issues)
        self._check_sycophantic_tests(filepath, content, issues)
        self._check_security_patterns(content, issues)
        self._check_token_waste(content, issues)

        warnings = [i for i in issues if i.severity == "warning"]
        status = "WARNINGS" if warnings else "OK"
        return AuditResult(file=filepath, status=status, issues=issues)

    def _check_invented_imports(
        self,
        filepath: str,
        content: str,
        file_dir: Path,
        issues: list[AuditIssue],
    ) -> None:
        imports = re.findall(r"(?:from|import)\s+([\w.]+)", content)
        for imp in imports:
            top = imp.split(".")[0]
            if top in _KNOWN_PACKAGES:
                continue

            parts = imp.split(".")
            found = self._resolve_import(file_dir, parts) or self._resolve_import(self.root, parts)

            if not found:
                issues.append(AuditIssue(
                    severity="warning",
                    type="import_unverified",
                    message=f"Verify import exists: {imp}",
                    line=self._find_line(content, imp),
                ))

    def _resolve_import(self, base: Path, parts: list[str]) -> bool:
        check_path = base
        for part in parts:
            if (check_path / f"{part}.py").exists():
                return True
            if (check_path / part).is_dir() and (check_path / part / "__init__.py").exists():
                return True
            check_path = check_path / part
        return False

    def _check_sycophantic_tests(
        self,
        filepath: str,
        content: str,
        issues: list[AuditIssue],
    ) -> None:
        is_test = (
            "test" in filepath.lower()
            or filepath.endswith(("_test.py", ".test.js", ".spec.ts", ".test.ts"))
        )
        if not is_test:
            return

        assertions = len(re.findall(r"assert|expect|should", content, re.IGNORECASE))
        test_funcs = len(re.findall(r"def\s+test_", content))
        if test_funcs > 0 and assertions < test_funcs:
            issues.append(AuditIssue(
                severity="info",
                type="weak_tests",
                message=f"Low assertions ({assertions}) vs test functions ({test_funcs})",
            ))

        if not re.search(r"(?:error|exception|edge|invalid|None|null|empty)", content, re.IGNORECASE):
            issues.append(AuditIssue(
                severity="info",
                type="missing_negative_tests",
                message="Consider adding edge case/error path tests",
            ))

    def _check_security_patterns(self, content: str, issues: list[AuditIssue]) -> None:
        patterns = [
            (r"\beval\s*\(", "Dangerous eval() - verify no user input reaches it"),
            (r"\bexec\s*\(", "Dangerous exec() - verify no user input reaches it"),
            (r"subprocess\.\w+\s*\([^)]*shell\s*=\s*True", "Subprocess with shell=True - injection risk"),
            (r"password\s*=\s*[\"'][^${}]+[\"']", "Hardcoded password - use environment variable"),
            (r"secret\s*=\s*[\"'][^${}\s]+[\"']", "Hardcoded secret - use environment variable"),
            (r"api_key\s*=\s*[\"'][^${}\s]{10,}[\"']", "Hardcoded API key - use environment variable"),
        ]
        for pattern, message in patterns:
            for match in re.finditer(pattern, content):
                line = content[: match.start()].count("\n") + 1
                issues.append(AuditIssue(
                    severity="warning",
                    type="security",
                    message=message,
                    line=line,
                ))

    def _check_token_waste(self, content: str, issues: list[AuditIssue]) -> None:
        long_names = re.findall(r"\b[a-z_]{30,}\b", content)
        if len(long_names) > 2:
            issues.append(AuditIssue(
                severity="info",
                type="verbose_names",
                message=f"{len(long_names)} very long variable names (>30 chars)",
            ))

        redundant = re.findall(
            r"#\s*(?:This is|Here we|This function|This method|This code)",
            content,
            re.IGNORECASE,
        )
        if len(redundant) > 3:
            issues.append(AuditIssue(
                severity="info",
                type="redundant_comments",
                message=f"{len(redundant)} comments restate the obvious",
            ))

        commented_blocks = re.findall(r"(?:^\s*#.*\n){15,}", content, re.MULTILINE)
        if commented_blocks:
            issues.append(AuditIssue(
                severity="info",
                type="dead_scaffolding",
                message=f"{len(commented_blocks)} large commented blocks - consider removing",
            ))

    @staticmethod
    def _find_line(content: str, pattern: str) -> Optional[int]:
        for i, line in enumerate(content.split("\n"), 1):
            if pattern in line:
                return i
        return None


def _get_staged_files() -> list[str]:
    """Return list of staged .py/.js/.ts files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        return [
            f for f in result.stdout.strip().split("\n")
            if f and f.endswith((".py", ".js", ".ts", ".tsx", ".jsx"))
        ]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


async def run(
    filepath: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Run preflight audit on a file or staged changes.

    Args:
        filepath: Specific file to audit. If None, audits staged git changes.
        verbose: Include all issues in output (default: summary only).

    Returns:
        Formatted audit report as a string. Always succeeds — advisory only.
    """
    cwd = str(Path.cwd())
    auditor = PreflightAuditor(cwd)
    results: list[AuditResult] = []

    if filepath:
        path = Path(filepath)
        if not path.exists():
            return f"[SKIP] {filepath} — file not found"
        content = path.read_text(errors="ignore")
        results.append(auditor.audit(filepath, content))
    else:
        staged = _get_staged_files()
        if not staged:
            return "[SKIP] No staged changes found — nothing to audit"
        for f in staged:
            path = Path(f)
            if not path.exists():
                continue
            content = path.read_text(errors="ignore")
            results.append(auditor.audit(f, content))

    lines: list[str] = []
    total_warnings = 0
    total_info = 0
    for result in results:
        warnings = [i for i in result.issues if i.severity == "warning"]
        info = [i for i in result.issues if i.severity == "info"]
        total_warnings += len(warnings)
        total_info += len(info)

        if verbose or result.status == "WARNINGS":
            lines.append(str(result))
        elif result.issues:
            lines.append(f"[OK] {result.file} ({len(info)} info)")

    lines.append("")
    lines.append(
        f"Preflight: {len(results)} file(s), {total_warnings} warning(s), {total_info} info(s)"
    )
    if total_warnings > 0:
        lines.append("Advisory only — escalate to impact-map skill if significant.")
    else:
        lines.append("No warnings.")

    return "\n".join(lines)
