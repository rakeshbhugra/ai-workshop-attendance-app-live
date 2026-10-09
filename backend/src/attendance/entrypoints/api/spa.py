"""Serve the built single-page app from FastAPI.

One process, one image, one origin: no nginx, no CORS in production, no separate
static host. The SPA's hashed assets are mounted at ``/assets`` and every other
unmatched path returns ``index.html`` so client-side routes survive a hard
refresh or a shared deep link.

**This must be registered last.** The catch-all matches literally everything, so
any route added after it is unreachable — including ``/docs``.

The set of real files is read **once, at startup**, not per request. Two reasons:
the handler then makes no blocking filesystem call on the event loop, and a
request can only ever be served a file that was in the build — so
``GET /../../etc/passwd`` cannot resolve to anything, by construction rather than
by getting a path check right.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from attendance.config.logging import get_logger

log = get_logger(__name__)


def mount_spa(app: FastAPI, frontend_dir: str) -> None:
    """No-op unless ``frontend_dir`` points at a real build. In dev that keeps
    FastAPI a pure API server while Vite serves the SPA with hot reload."""
    root = Path(frontend_dir).resolve() if frontend_dir else None
    if root is None or not root.is_dir():
        log.info("spa_not_mounted", frontend_dir=frontend_dir or "(unset)")
        return

    index_html = root / "index.html"
    if not index_html.is_file():
        # A built dist without an index.html means the frontend build stage
        # failed but the image still got published. Fail loudly at startup
        # rather than serving 404s to users.
        raise RuntimeError(f"{frontend_dir} has no index.html — was the SPA built?")

    # Every static file the build produced, keyed by its URL path. Includes
    # assets/, favicon.ico, robots.txt, manifest.webmanifest and anything else
    # dropped in public/.
    static_files = {str(path.relative_to(root)): path for path in root.rglob("*") if path.is_file()}

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        # A known build artefact is served as itself; everything else is a
        # client-side route and gets the shell.
        target = static_files.get(full_path)
        return FileResponse(target if target is not None else index_html)

    log.info("spa_mounted", frontend_dir=str(root), files=len(static_files))
