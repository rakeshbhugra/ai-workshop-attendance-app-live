"""Shared schema types.

``UtcDatetime`` exists because of a bug that is easy to ship and unpleasant to
find. SQLite ignores ``DateTime(timezone=True)`` and hands back *naive*
datetimes; Postgres hands back aware ones. So the same endpoint serialises
``...T12:00:00Z`` when it returns a freshly created object and
``...T12:00:00`` when it returns one read back from SQLite — and a browser
parses that second form as **local** time, silently shifting every timestamp by
the user's UTC offset.

Normalising at the wire boundary means the API contract is "always UTC, always
aware", whatever the storage engine underneath happens to do. Use it for every
datetime that leaves the app.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def _as_utc(value: datetime) -> datetime:
    # Naive values are assumed UTC — true here because the domain only ever
    # creates timezone-aware UTC timestamps (see services/notes.py::_now).
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]
