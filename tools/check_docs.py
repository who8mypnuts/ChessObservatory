#!/usr/bin/env python3
"""Documentation freshness checks (CI job ``docs-freshness``).

What is enforced:

* every relative Markdown link in ``README.md`` and ``docs/`` resolves to a file;
* every ADR file is listed in ``docs/adr/README.md``;
* every ADR has a title and the four required sections;
* the documentation set the plan promises exists.

No third-party dependencies: this runs before anything is installed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ADR_DIR = DOCS / "adr"
ADR_INDEX = ADR_DIR / "README.md"

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "ftp://")
REQUIRED_DOCS = (
    "docs/README.md",
    "docs/architecture.md",
    "docs/position-api.md",
    "docs/search.md",
    "docs/metrics.md",
    "docs/models.md",
    "docs/themes.md",
    "docs/user/README.md",
    "docs/gallery/README.md",
    "docs/adr/README.md",
)
ADR_SECTIONS = ("## Status", "## Context", "## Decision", "## Consequences")


def markdown_files() -> list[Path]:
    files = [ROOT / "README.md"]
    files.extend(sorted(DOCS.rglob("*.md")))
    return files


def outside_code_fences(text: str) -> str:
    kept: list[str] = []
    inside = False
    for line in text.splitlines():
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept)


def link_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw in LINK.findall(outside_code_fences(text)):
        target = raw.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split(" ", 1)[0]
        if not target or target.startswith("#") or target.startswith(EXTERNAL):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


def check_links() -> list[str]:
    problems: list[str] = []
    for path in markdown_files():
        if not path.is_file():
            problems.append(f"missing file: {path.relative_to(ROOT)}")
            continue
        for target in link_targets(path.read_text(encoding="utf-8")):
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                problems.append(f"{path.relative_to(ROOT)}: broken link '{target}'")
    return problems


def adr_files() -> list[Path]:
    return sorted(ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md"))


def check_adrs() -> list[str]:
    problems: list[str] = []
    if not ADR_INDEX.is_file():
        return [f"missing ADR index: {ADR_INDEX.relative_to(ROOT)}"]
    index_text = ADR_INDEX.read_text(encoding="utf-8")
    for path in adr_files():
        text = path.read_text(encoding="utf-8")
        name = path.name
        if name not in index_text:
            problems.append(f"ADR not listed in docs/adr/README.md: {name}")
        first = text.lstrip().splitlines()[0] if text.strip() else ""
        if not first.startswith(f"# ADR-{name[:4]}"):
            problems.append(f"{name}: title must start with '# ADR-{name[:4]}'")
        for section in ADR_SECTIONS:
            if section not in text:
                problems.append(f"{name}: missing section '{section}'")
    return problems


def check_required() -> list[str]:
    return [
        f"missing required doc: {item}" for item in REQUIRED_DOCS if not (ROOT / item).is_file()
    ]


def main() -> int:
    problems = [*check_required(), *check_links(), *check_adrs()]
    if problems:
        print("Documentation check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    links = sum(len(link_targets(path.read_text(encoding="utf-8"))) for path in markdown_files())
    print(
        f"docs check: {len(markdown_files())} files, {links} relative links, "
        f"{len(adr_files())} ADRs \u2014 ok"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
