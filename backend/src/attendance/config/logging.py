"""Structured logging via structlog.

Two things this buys over ``logging.basicConfig``:

* **Machine-readable output in deployed environments.** One JSON object per line
  means you query ``request_id="abc"`` instead of grepping a string.
* **Context that follows the request.** ``bind_contextvars`` in the middleware
  attaches the request id once, and every log line in that request carries it —
  including lines from deep inside a service that has no idea a request exists.

Uvicorn configures only its own loggers, so without ``configure_stdlib_logging``
the root logger keeps logging's WARNING-only fallback and every ``log.info()``
in the app is silently dropped. That is a genuinely confusing hour to lose.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(*, level: str = "INFO", json_output: bool = False) -> None:
    """Call once, as early as possible in application startup."""
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    structlog.configure(
        processors=[
            # Pull anything bound by the middleware (request_id, path, ...) into
            # every event dict.
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[level.upper()]
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bring stdlib loggers (uvicorn, sqlalchemy, boto3) up to the same level so
    # their output isn't swallowed or, worse, duplicated at a different format.
    logging.basicConfig(level=level.upper(), format="%(message)s", force=True)
    # botocore logs every request signature at DEBUG and httpx logs a line per
    # outgoing call at INFO. Both are noise, not signal, at our default level.
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """``log = get_logger(__name__)`` at the top of a module."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
