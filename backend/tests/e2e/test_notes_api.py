"""End-to-end tests — real HTTP semantics through the real app.

The top of the pyramid: the fewest tests, covering what only this tier can see —
status codes, URL shapes, serialisation, and the wiring between layers. Business
rules are *not* re-tested here; they were covered in ``tests/unit`` for a
thousandth of the cost.

A useful smell check: if this file is where you instinctively add a test for a
new rule, the rule probably isn't in the domain yet.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

API = "/api/v1"


async def test_create_then_read_a_note(client: AsyncClient):
    created = await client.post(f"{API}/notes", json={"title": "Groceries", "body": "milk"})

    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Groceries"
    assert body["is_archived"] is False

    fetched = await client.get(f"{API}/notes/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


async def test_listing_notes(client: AsyncClient):
    await client.post(f"{API}/notes", json={"title": "One", "body": ""})
    await client.post(f"{API}/notes", json={"title": "Two", "body": ""})

    response = await client.get(f"{API}/notes")

    assert response.status_code == 200
    assert {n["title"] for n in response.json()} == {"One", "Two"}


async def test_an_unknown_note_is_a_404(client: AsyncClient):
    """Proves the NotFoundError → 404 mapping in exception_handlers.py is wired
    up. The service raises a domain error and never mentions HTTP."""
    response = await client.get(f"{API}/notes/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "detail" in response.json()


async def test_a_broken_business_rule_is_a_409(client: AsyncClient):
    """ConflictError → 409, same mapping, different base class."""
    note = (await client.post(f"{API}/notes", json={"title": "Groceries"})).json()
    await client.post(f"{API}/notes/{note['id']}/archive")

    response = await client.post(f"{API}/notes/{note['id']}/archive")

    assert response.status_code == 409


async def test_a_blank_title_is_rejected_by_the_domain_as_a_422(client: AsyncClient):
    # Passes Pydantic (it is a string of the right length) and is then caught by
    # the domain rule — which is exactly why that rule lives in the domain and
    # not only in the schema.
    response = await client.post(f"{API}/notes", json={"title": "   ", "body": ""})

    assert response.status_code == 422


async def test_archive_then_restore_round_trip(client: AsyncClient):
    note = (await client.post(f"{API}/notes", json={"title": "Groceries"})).json()

    archived = await client.post(f"{API}/notes/{note['id']}/archive")
    assert archived.json()["is_archived"] is True

    # Archived notes drop out of the default list and come back with the flag.
    assert note["id"] not in {n["id"] for n in (await client.get(f"{API}/notes")).json()}
    with_archived = await client.get(f"{API}/notes", params={"include_archived": True})
    assert note["id"] in {n["id"] for n in with_archived.json()}

    restored = await client.post(f"{API}/notes/{note['id']}/restore")
    assert restored.json()["is_archived"] is False


async def test_delete_returns_204_and_the_note_is_gone(client: AsyncClient):
    note = (await client.post(f"{API}/notes", json={"title": "Groceries"})).json()

    deleted = await client.delete(f"{API}/notes/{note['id']}")

    assert deleted.status_code == 204
    assert (await client.get(f"{API}/notes/{note['id']}")).status_code == 404


async def test_health_is_outside_the_version_prefix(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
