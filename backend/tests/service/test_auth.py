from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from attendance.adapters.auth.fakes import FakeProvider, FakeSessionTokens
from attendance.adapters.auth.tokens import SignedSessionTokens
from attendance.adapters.unit_of_work_fake import FakeUnitOfWork
from attendance.domain.exceptions import AuthenticationError
from attendance.domain.user import ExternalIdentity
from attendance.services.auth import AuthService

NOW = datetime(2026, 10, 9, tzinfo=UTC)
GOOGLE = ExternalIdentity("google", "g-1", "a@example.com", "A", email_verified=True)
OTHER = ExternalIdentity("other", "o-1", "a@example.com", "A", email_verified=False)


def service(uow: FakeUnitOfWork, *providers: FakeProvider, domains: str = "") -> AuthService:
    allowed = frozenset(domains.split()) if domains else frozenset()
    return AuthService(
        uow, {p.name: p for p in providers}, FakeSessionTokens(), allowed_domains=allowed
    )


async def test_first_sign_in_registers_then_reuses_the_user(uow: FakeUnitOfWork):
    auth = service(uow, FakeProvider("google", GOOGLE))
    user, token = await auth.complete("google", "good", redirect_uri="cb", now=NOW)
    again, _ = await auth.complete("google", "good", redirect_uri="cb", now=NOW)
    assert again.id == user.id and len(uow.users.items) == 1
    assert (await auth.current_user(token)).email == "a@example.com"


async def test_verified_email_links_a_second_provider_to_the_same_user(uow: FakeUnitOfWork):
    auth = service(uow)
    a = await auth.sign_in(OTHER, NOW)
    b = await auth.sign_in(GOOGLE, NOW)
    assert a.id == b.id and len(uow.users.identities) == 2


async def test_unverified_email_never_claims_an_existing_account(uow: FakeUnitOfWork):
    auth = service(uow)
    a = await auth.sign_in(GOOGLE, NOW)
    b = await auth.sign_in(OTHER, NOW)
    assert a.id != b.id


async def test_domain_rule_refuses_other_domains(uow: FakeUnitOfWork):
    auth = service(uow, domains="corp.com")
    with pytest.raises(AuthenticationError):
        await auth.sign_in(GOOGLE, NOW)
    assert not uow.users.items


async def test_bad_or_missing_session_is_not_signed_in(uow: FakeUnitOfWork):
    auth = service(uow)
    for token in (None, "junk", str(uuid.uuid4())):
        with pytest.raises(AuthenticationError):
            await auth.current_user(token)


def test_signed_tokens_reject_tampering_and_other_secrets():
    tokens = SignedSessionTokens("s1", max_age_seconds=60)
    user_id = uuid.uuid4()
    token = tokens.issue(user_id)
    assert tokens.read(token) == user_id
    assert tokens.read(token + "x") is None
    assert SignedSessionTokens("s2", max_age_seconds=60).read(token) is None


async def test_google_requires_verified_staff_email(uow: FakeUnitOfWork):
    auth = AuthService(uow, {}, FakeSessionTokens(), allowed_emails=frozenset({"a@example.com"}))
    with pytest.raises(AuthenticationError):
        await auth.sign_in(ExternalIdentity("google", "g", "a@example.com", "A", False), NOW)
    with pytest.raises(AuthenticationError):
        await auth.sign_in(ExternalIdentity("google", "g", "b@example.com", "B", True), NOW)
    user = await auth.sign_in(GOOGLE, NOW)
    assert user.email == "a@example.com"
    dev = ExternalIdentity("dev", "dev", "dev@localhost", "Developer", True)
    assert (await auth.sign_in(dev, NOW)).email == "dev@localhost"
