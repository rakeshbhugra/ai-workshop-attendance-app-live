"""Session tokens: the user id, signed and timestamped. Nothing is stored
server-side, so there is no session table to clean up. Expiry is enforced on
read. Rotate the secret to log everyone out."""

from __future__ import annotations

import uuid

from itsdangerous import BadSignature, URLSafeTimedSerializer

from attendance.ports.auth import SessionTokens


class SignedSessionTokens(SessionTokens):
    def __init__(self, secret: str, *, max_age_seconds: int) -> None:
        self._serializer = URLSafeTimedSerializer(secret, salt="session")
        self._max_age = max_age_seconds

    def issue(self, user_id: uuid.UUID) -> str:
        return str(self._serializer.dumps(str(user_id)))

    def read(self, token: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(self._serializer.loads(token, max_age=self._max_age))
        except (BadSignature, ValueError):
            return None
