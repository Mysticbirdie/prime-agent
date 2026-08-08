#!/usr/bin/env python3
"""Birdhouse bootstrap — seed prime-agent's continual harness from project docs.

Reads a project's AGENTS.md and CLAUDE.md (or any similar rules files) and
creates harness prompt entries for each invariant, gotcha, and constraint.
Idempotent — skips entries that already exist.

Usage:
    python scripts/birdhouse_bootstrap.py /path/to/project
    python scripts/birdhouse_bootstrap.py /path/to/project --dry-run
    python scripts/birdhouse_bootstrap.py .  # current directory

This bridges existing project documentation into prime-agent's memory system
without manual entry. The agent then has the project's invariants available
as supplemental prompt notes in every session.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_agents_md(content: str) -> list[dict]:
    """Extract invariants, gotchas, and constraints from AGENTS.md.

    Looks for:
    - Numbered list items under 'invariants' or 'always-on' sections
    - Bullet points under 'Gotchas' sections
    - Constraint-style rules (Never, Always, No, Must)
    """
    entries: list[dict] = []
    lines = content.split("\n")
    current_section = ""
    in_gotchas = False
    in_invariants = False

    for line in lines:
        stripped = line.strip()

        # Track section headers
        if stripped.startswith("#"):
            header = stripped.lower()
            in_invariants = "invariant" in header or "always-on" in header
            in_gotchas = "gotcha" in header
            current_section = stripped.lstrip("#").strip()
            continue

        # Numbered invariants (e.g., "1. **Era-locking**: ...")
        if in_invariants and re.match(r"^\d+\.\s+\*\*[^*]+\*\*", stripped):
            match = re.match(r"^\d+\.\s+\*\*([^*]+)\*\*:\s*(.+)", stripped)
            if match:
                title = match.group(1).strip()
                content_text = match.group(2).strip()
                entries.append({
                    "kind": "prompt",
                    "title": f"Invariant: {title}",
                    "content": content_text,
                    "path": "invariants",
                })

        # Gotcha bullets (e.g., "- **Flat depth maps are...**")
        if in_gotchas and stripped.startswith("- "):
            # Remove the leading dash and any bold markers
            text = stripped[2:]
            # Extract title from bold if present
            bold_match = re.match(r"\*\*([^*]+)\*\*[:\s]*(.+)", text)
            if bold_match:
                title = bold_match.group(1).strip()
                content_text = bold_match.group(2).strip()
            else:
                # Use first sentence as title
                parts = text.split(". ", 1)
                title = parts[0].strip().rstrip(".")
                content_text = text
            entries.append({
                "kind": "prompt",
                "title": f"Gotcha: {title}",
                "content": content_text,
                "path": "gotchas",
            })

        # Constraint-style rules anywhere (Never..., Always..., No ..., Must...)
        constraint_match = re.match(
            r"^(?:-\s+)?\*\*(Never|Always|No|Must|Do not|Don't)\b\*\*[:\s]*(.+)",
            stripped,
        )
        if constraint_match:
            keyword = constraint_match.group(1)
            text = constraint_match.group(2).strip()
            entries.append({
                "kind": "prompt",
                "title": f"Constraint: {keyword} {text[:60]}",
                "content": f"{keyword} {text}",
                "path": "constraints",
            })

    return entries


def parse_claude_md(content: str) -> list[dict]:
    """Extract gotchas from CLAUDE.md's Gotchas section."""
    entries: list[dict] = []
    lines = content.split("\n")
    in_gotchas = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            in_gotchas = "gotcha" in stripped.lower()
            continue

        if in_gotchas and stripped.startswith("- "):
            text = stripped[2:]
            bold_match = re.match(r"\*\*([^*]+)\*\*[:\s]*(.+)", text)
            if bold_match:
                title = bold_match.group(1).strip()
                content_text = bold_match.group(2).strip()
            else:
                parts = text.split(". ", 1)
                title = parts[0].strip().rstrip(".")
                content_text = text
            entries.append({
                "kind": "prompt",
                "title": f"Gotcha: {title}",
                "content": content_text,
                "path": "gotchas",
            })

    return entries


def slugify(text: str) -> str:
    """Create a stable ID from text."""
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:80] if s else "entry"


def load_harness_state(harness_dir: Path) -> dict:
    """Load the global harness state, or return empty state."""
    state_path = harness_dir / "harness_state.json"
    if not state_path.exists():
        return {
            "schema": 1,
            "entries": {"prompt": {}, "memory": {}, "skill": {}, "subagent": {}},
            "refinements": [],
        }
    try:
        return json.loads(state_path.read_text())
    except (ValueError, OSError):
        return {
            "schema": 1,
            "entries": {"prompt": {}, "memory": {}, "skill": {}, "subagent": {}},
            "refinements": [],
        }


def save_harness_state(harness_dir: Path, state: dict) -> Path:
    """Save harness state atomically."""
    import os
    import tempfile

    state_path = harness_dir / "harness_state.json"
    harness_dir.mkdir(parents=True, exist_ok=True)

    # Atomic write via temp file + rename
    fd, tmp_path = tempfile.mkstemp(dir=str(harness_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, str(state_path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return state_path


def bootstrap(project_dir: str, dry_run: bool = False) -> str:
    """Seed the continual harness from project documentation.

    Args:
        project_dir: Path to the project root.
        dry_run: If True, print what would be created without writing.

    Returns:
        Summary of what was done.
    """
    root = Path(project_dir).resolve()
    if not root.exists():
        return f"ERROR: {root} does not exist"

    # Collect entries from all rules files
    entries: list[dict] = []

    agents_md = root / "AGENTS.md"
    if agents_md.exists():
        entries.extend(parse_agents_md(agents_md.read_text()))

    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        entries.extend(parse_claude_md(claude_md.read_text()))

    # Also check .devin/ for seed bank
    seed_bank = root / ".devin" / "memory-bank.seed.json"
    if seed_bank.exists():
        try:
            bank = json.loads(seed_bank.read_text())
            for item in bank.get("knowledge", []):
                entries.append({
                    "kind": "prompt",
                    "title": f"{item.get('category', 'rule')}: {item.get('id', '')}",
                    "content": item.get("content", ""),
                    "path": f"seed-bank/{item.get('category', 'general')}",
                })
            for item in bank.get("procedural", []):
                entries.append({
                    "kind": "prompt",
                    "title": f"procedure: {item.get('id', '')}",
                    "content": item.get("content", ""),
                    "path": f"seed-bank/{item.get('category', 'procedural')}",
                })
        except (ValueError, OSError):
            pass

    if not entries:
        return f"[SKIP] No AGENTS.md, CLAUDE.md, or memory-bank.seed.json found in {root}"

    # Deduplicate by normalized content (case-insensitive, whitespace-normalized,
    # prefix-stripped). This catches the same invariant appearing in both
    # AGENTS.md and the seed bank with slightly different formatting or prefixes.
    def normalize(text: str) -> str:
        # Strip common prefixes like "Era-locking:" or "Invariant:"
        cleaned = re.sub(r"^[A-Z][\w-]+:\s*", "", text)
        return re.sub(r"\s+", " ", cleaned.lower().strip())

    seen_content: set[str] = set()
    unique_entries: list[dict] = []
    for entry in entries:
        key = normalize(entry["content"])
        if key not in seen_content:
            seen_content.add(key)
            unique_entries.append(entry)

    # Resolve harness directory
    agent_dir = Path.home() / ".prime" / "agent"
    harness_dir = agent_dir / "harness"
    state = load_harness_state(harness_dir) if not dry_run else {
        "schema": 1,
        "entries": {"prompt": {}, "memory": {}, "skill": {}, "subagent": {}},
        "refinements": [],
    }

    # Add entries that don't already exist
    existing_ids = set(state["entries"].get("prompt", {}).keys())
    added = 0
    skipped = 0

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    for entry in unique_entries:
        entry_id = slugify(entry["title"])
        if entry_id in existing_ids:
            skipped += 1
            continue

        state["entries"]["prompt"][entry_id] = {
            "id": entry_id,
            "kind": "prompt",
            "title": entry["title"],
            "content": entry["content"],
            "path": entry["path"],
            "scope": "global",
            "reference": {},
            "arguments": {},
            "metadata": {"source": "birdhouse-bootstrap", "project": root.name},
            "source": "birdhouse-bootstrap",
            "created_at": now,
            "updated_at": now,
            "version": 1,
        }
        added += 1
        existing_ids.add(entry_id)

    if dry_run:
        lines = [f"[DRY RUN] Would add {added} prompt entries, skip {skipped} existing"]
        for entry in unique_entries:
            entry_id = slugify(entry["title"])
            if entry_id not in existing_ids or added > 0:
                lines.append(f"  + [{entry_id}] {entry['title']}")
        return "\n".join(lines)

    if added > 0:
        save_harness_state(harness_dir, state)

    return (
        f"Bootstrap complete: {added} entries added, {skipped} skipped (already exist)\n"
        f"Harness state: {harness_dir / 'harness_state.json'}\n"
        f"Source: {root.name}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed prime-agent's continual harness from project docs"
    )
    parser.add_argument("project_dir", help="Path to the project root")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    result = bootstrap(args.project_dir, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
