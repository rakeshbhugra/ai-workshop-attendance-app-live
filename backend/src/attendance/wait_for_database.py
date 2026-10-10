"""Wait for the configured database before migrations and server startup."""

from __future__ import annotations

import asyncio

from attendance.config.database import dispose_engine
from attendance.config.database_readiness import check_database
from attendance.config.logging import configure_logging, get_logger
from attendance.config.settings import get_settings

log = get_logger(__name__)


async def wait_for_database() -> None:
    """Retry transient failures, but fail startup when the total deadline expires."""
    settings = get_settings()
    try:
        async with asyncio.timeout(settings.db_startup_timeout_seconds):
            while True:
                try:
                    await check_database()
                except Exception:  # noqa: BLE001 - retry connectivity failures until deadline
                    # Driver errors may contain credentials; log only the retry event.
                    log.warning("database_startup_waiting")
                    await asyncio.sleep(settings.db_startup_retry_seconds)
                else:
                    log.info("database_startup_ready")
                    return
    finally:
        await dispose_engine()


def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    try:
        asyncio.run(wait_for_database())
    except TimeoutError:
        log.error("database_startup_timeout", timeout_seconds=settings.db_startup_timeout_seconds)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
