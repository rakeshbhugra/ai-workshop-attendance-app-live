"""Domain errors.

The domain raises these; it knows nothing about HTTP. The API layer maps the
three base classes onto status codes exactly once, in
``entrypoints/api/exception_handlers.py`` — so a new domain error gets the right
status for free as long as it subclasses one of them.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for every business-rule violation. Never raised directly."""


class NotFoundError(DomainError):
    """The thing you asked for does not exist. -> HTTP 404."""


class ConflictError(DomainError):
    """The thing exists but is in the wrong state for this operation. -> HTTP 409."""


class ValidationError(DomainError):
    """The input breaks a business rule (not a schema rule). -> HTTP 422.

    Shape/type validation belongs in the Pydantic schema at the edge. This is for
    rules that are part of the business, e.g. "a note title cannot be blank".
    """


class AuthenticationError(DomainError):
    """Not signed in, or the sign-in attempt was refused. -> HTTP 401."""
