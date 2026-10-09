#!/usr/bin/env python3
"""Keep files small enough to hold in your head.

    python3 scripts/check_file_length.py            # warn at 150, fail at 250
    python3 scripts/check_file_length.py --list     # show the worst offenders

**It counts code lines, not total lines.** Blank lines, comments and docstrings
are excluded. That is deliberate: a length limit that counts comments is a limit
on explaining yourself, and people respond to it by deleting the comments rather
than by splitting the file. What we actually care about is how much *behaviour*
lives in one place.

Two thresholds, for two different jobs:

    150   advisory. The review skill flags it and suggests a split.
    250   hard failure. CI stops here.

The gap is on purpose. Some files are legitimately long — a table of constants,
generated types, a big mapping — and blocking a merge at 3am over one of those
teaches people to bypass the gate. Genuine exceptions opt out with a comment
reading `file-length-exempt: <reason>` (written as a `#` or `//` comment). The
reason is required, because "why is this file allowed to be huge" is exactly
what the next reader needs to know.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WARN_AT = 150
FAIL_AT = 250

SEARCH_PATHS = ["backend/src", "backend/tests", "frontend/src", "scripts"]
EXTENSIONS = {".py", ".ts", ".tsx"}
SKIP_DIRS = {"node_modules", ".venv", "dist", "__pycache__", ".mypy_cache", ".ruff_cache"}

# Anchored to the start of a comment line, so a file that merely *documents* the
# marker (like this one) isn't treated as exempting itself.
EXEMPT = re.compile(r"^[ \t]*(?:#|//)[ \t]*file-length-exempt:[ \t]*(?P<reason>\S.*)$", re.MULTILINE)


def python_code_lines(source: str) -> int:
    """Non-blank, non-comment, non-docstring lines."""
    docstring_lines: set[int] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _naive_count(source, comment_prefix="#")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        # A docstring is a bare string expression at the top of a block.
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and first.end_lineno is not None
        ):
            docstring_lines.update(range(first.lineno, first.end_lineno + 1))

    count = 0
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or number in docstring_lines:
            continue
        count += 1
    return count


def typescript_code_lines(source: str) -> int:
    """Non-blank lines outside `//` comments and `/* ... */` blocks."""
    count = 0
    in_block = False
    for raw in source.splitlines():
        line = raw.strip()
        if in_block:
            if "*/" in line:
                in_block = False
                line = line.split("*/", 1)[1].strip()
                if not line:
                    continue
            else:
                continue
        if not line or line.startswith("//"):
            continue
        if line.startswith("/*"):
            # A block comment that also closes on this line leaves no code
            # behind unless something follows the */.
            if "*/" not in line:
                in_block = True
                continue
            if not line.split("*/", 1)[1].strip():
                continue
        count += 1
    return count


def _naive_count(source: str, *, comment_prefix: str) -> int:
    return sum(
        1
        for line in source.splitlines()
        if line.strip() and not line.strip().startswith(comment_prefix)
    )


def collect() -> list[tuple[Path, int, str | None]]:
    """(path, code_lines, exemption_reason) for every source file."""
    results: list[tuple[Path, int, str | None]] = []
    for search in SEARCH_PATHS:
        base = ROOT / search
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.suffix not in EXTENSIONS or not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            lines = python_code_lines(source) if path.suffix == ".py" else typescript_code_lines(source)
            match = EXEMPT.search(source)
            reason = match.group("reason").strip() if match else None
            results.append((path.relative_to(ROOT), lines, reason))
    return sorted(results, key=lambda item: item[1], reverse=True)


def main(argv: list[str]) -> int:
    files = collect()
    if "--list" in argv:
        for path, lines, reason in files[:25]:
            flag = "exempt" if reason else ("FAIL" if lines > FAIL_AT else "warn" if lines > WARN_AT else "ok")
            print(f"{lines:5}  {flag:6}  {path}")
        return 0

    failures = [(p, n) for p, n, reason in files if n > FAIL_AT and reason is None]
    warnings = [(p, n) for p, n, reason in files if WARN_AT < n <= FAIL_AT]

    for path, lines in warnings:
        print(f"note: {path} is {lines} code lines (guideline is {WARN_AT}) — consider splitting it.")

    if failures:
        print(f"\nFiles over the hard limit of {FAIL_AT} code lines:\n", file=sys.stderr)
        for path, lines in failures:
            print(f"  {path}  ({lines} code lines)", file=sys.stderr)
        print(
            "\nSplit them, or add a comment explaining why this one has to be long:\n"
            "  # file-length-exempt: <reason>",
            file=sys.stderr,
        )
        return 1

    print(f"✓ no file over {FAIL_AT} code lines ({len(warnings)} over the {WARN_AT} guideline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
