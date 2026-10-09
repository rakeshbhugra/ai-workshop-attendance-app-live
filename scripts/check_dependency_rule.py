#!/usr/bin/env python3
"""Enforce the dependency rule.

    domain      ->  imports nothing internal (stdlib only)
    ports       ->  domain
    adapters    ->  domain, ports, config, external SDKs
    services    ->  domain, ports
    entrypoints ->  domain, ports, services, config, schemas
    config      ->  (nothing internal)
    bootstrap   ->  everything (it is the wiring)

Dependencies point *inward*, toward the domain. This is the architecture; the
folder names are just labels. Without a check like this the rule survives about
three sprints — someone imports a SQLAlchemy session into a service because it
is quicker, and the layering quietly stops being real.

Runs in CI and in `make lint`. It is deliberately ~100 lines of stdlib with no
dependencies, so it never breaks and nobody is tempted to delete it.

    python3 scripts/check_dependency_rule.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PACKAGE = "attendance"
SRC = Path(__file__).resolve().parent.parent / "backend" / "src" / PACKAGE

# Which internal layers each layer may import from.
ALLOWED: dict[str, set[str]] = {
    "domain": set(),
    "ports": {"domain"},
    "config": set(),
    # Adapters implement ports using real infrastructure, and read settings to
    # know which infrastructure. They must never reach up into services.
    "adapters": {"domain", "ports", "config"},
    # Services orchestrate the domain through ports. Importing an adapter here
    # is the single most common violation, and it is what makes services
    # untestable without a database.
    "services": {"domain", "ports"},
    "entrypoints": {"domain", "ports", "services", "config", "bootstrap"},
    # The composition root. Its whole job is to know every concrete class.
    "bootstrap": {"domain", "ports", "adapters", "services", "config"},
    "main": {"domain", "ports", "adapters", "services", "config", "entrypoints", "bootstrap"},
}

# Third-party packages no domain module may import, whatever the layer rules
# say. The domain being pure Python is what makes it fast to test and portable
# across the ORM/framework changes this app will outlive.
FORBIDDEN_IN_DOMAIN = {"sqlalchemy", "fastapi", "pydantic", "boto3", "starlette", "httpx"}


def layer_of(path: Path) -> str:
    """The layer a file belongs to: its first path segment under the package."""
    relative = path.relative_to(SRC)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def imported_modules(tree: ast.AST) -> list[tuple[str, int]]:
    """Every module name imported, with its line number."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.module, node.lineno))
    return found


def main() -> int:
    if not SRC.is_dir():
        print(f"error: {SRC} not found — run this from the repo root.", file=sys.stderr)
        return 2

    violations: list[str] = []

    for file in sorted(SRC.rglob("*.py")):
        source_layer = layer_of(file)
        allowed = ALLOWED.get(source_layer)
        if allowed is None:
            continue  # an unlisted top-level module; nothing to enforce
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        location = file.relative_to(SRC.parent.parent.parent)

        for module, line in imported_modules(tree):
            root = module.split(".")[0]

            if source_layer == "domain" and root in FORBIDDEN_IN_DOMAIN:
                violations.append(
                    f"{location}:{line}: domain imports '{module}'. The domain must be "
                    f"plain Python — move this to an adapter."
                )
                continue

            if root != PACKAGE:
                continue  # stdlib or third-party, and allowed at this layer

            parts = module.split(".")
            target_layer = parts[1] if len(parts) > 1 else ""
            if not target_layer or target_layer == source_layer:
                continue

            if target_layer not in allowed:
                permitted = ", ".join(sorted(allowed)) or "nothing internal"
                violations.append(
                    f"{location}:{line}: {source_layer} imports {target_layer} "
                    f"('{module}'). {source_layer} may only import: {permitted}."
                )

    if violations:
        print("Dependency rule violated — dependencies must point inward:\n", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "\nSee docs/architecture.md. If a service needs an adapter, it needs a "
            "port instead.",
            file=sys.stderr,
        )
        return 1

    print("✓ dependency rule holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
