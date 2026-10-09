# Testing

Four tiers, mirroring the layers. The architecture exists partly to make the
cheap tiers possible — if you find yourself writing everything as e2e tests, the
business logic is in the wrong layer.

| Tier | Location | Tests | Doubles | Speed | How many |
|---|---|---|---|---|---|
| **Unit** | `tests/unit/` | domain rules | none | ~1ms | lots |
| **Service** | `tests/service/` | use cases | `FakeUnitOfWork` | ~10ms | fewer |
| **Integration** | `tests/integration/` | real adapters | real database | ~100ms | few |
| **E2E** | `tests/e2e/` | HTTP contract | real app, fake infra | ~1s | fewest |

Run them: `make test-be`, `make test-fe`, or `make check` for everything CI runs.

---

## Which tier does this test belong in?

Ask what would have to break for this test to fail.

- **A business rule is wrong** → unit. No fixtures, no async, no database. Rules
  are cheap to test here and expensive everywhere else.
- **A use case forgot a step** (didn't commit, didn't check existence, called
  the wrong entity method) → service, with `FakeUnitOfWork`.
- **The SQL is wrong** (bad ordering, a mapping that drops a column, a rollback
  that doesn't) → integration.
- **The HTTP contract is wrong** (status code, URL, JSON shape) → e2e.

Test each rule **once**, at the cheapest tier that can see it. That
`archive()`-twice raises is a domain test; asserting it again through the service
and again through HTTP triples the cost of every future change to that rule. The
one e2e test that *is* worth having for it asserts the 409 — that is the mapping,
not the rule.

---

## Fakes, not mocks

`FakeNoteRepository` is a real working implementation backed by a dict. Tests
assert on **the state it ends up in**, never on which methods were called:

```python
# good — asserts an outcome
await service.create(title="Groceries", body="milk")
assert await uow.notes.get(note.id) is not None
assert uow.committed

# bad — asserts an implementation detail, breaks on any refactor
repo.add.assert_called_once_with(note)
```

A mock encodes *how* the service works today; a fake checks *what* it achieved.
The second survives refactoring, which is the whole point of having the tests.

**The fake must obey the same contract as the real adapter.** If
`SqlAlchemyNoteRepository.list()` is newest-first, so is the fake. When they
drift, your service suite is green for the wrong reason — which is exactly what
the integration tier is for. `tests/integration/test_note_repository.py`
deliberately re-asserts, against real SQL, things the service tests asserted
against the fake.

---

## Fixtures

Defined in `tests/conftest.py`:

| Fixture | Gives you |
|---|---|
| `uow` | a `FakeUnitOfWork` — the service-test workhorse |
| `session` / `session_factory` | a schema-fresh in-memory SQLite database per test |
| `client` | the whole app over ASGI (no network, no port), with the database and object storage overridden |

The `client` fixture builds the app exactly as production does and then swaps
only the two things that touch the outside world, via FastAPI's
`dependency_overrides`. That seam is why e2e tests here take milliseconds instead
of needing a running server.

### The SQLite caveat

Tests run against in-memory SQLite: fast, no container, schema-fresh per test.
It cannot catch dialect-specific behaviour — JSONB operators, `ON CONFLICT`
variants, constraint-violation error types, and timezone handling all differ.

That last one is not hypothetical: SQLite ignores `DateTime(timezone=True)` and
returns naive datetimes where Postgres returns aware ones. The template closes it
at the wire boundary with `UtcDatetime` (`schemas/common.py`) — use it for every
datetime you expose, or the same endpoint will emit two different formats.

Run the suite against Postgres in CI as well once the app uses anything
Postgres-specific.

---

## Coverage

`--cov-fail-under=80`, configured in `pyproject.toml`. It is a **ratchet**: raise
it as coverage grows, never lower it to make a build pass. Lowering it is how a
coverage gate becomes decoration.

Coverage measures which lines ran, not whether they were checked. 100% coverage
with no assertions is worthless; a well-chosen 80% is not. Use it to find
*untouched* code, not to prove code is tested.

---

## Frontend

Vitest + Testing Library. `renderWithProviders` (`src/test/utils.tsx`) wraps a
component in the same providers `main.tsx` uses, so a test exercises it the way
the app actually mounts it.

Two conventions:

**Query by role and label, not by CSS class.**

```tsx
screen.getByRole("button", { name: /add note/i })   // survives a restyle
screen.getByLabelText(/note title/i)
```

A test written this way fails when the feature breaks and passes when only the
styling changed — and it doubles as a light accessibility check, because an
element with no accessible name cannot be found this way.

**Stub `fetch`, not the hooks.** That keeps the real Query cache, the real
mutation flow and the real error mapping inside the test, so what's under test is
the wiring between them rather than a mock of it. `mockFetchSequence` takes a
queue of responses in call order.

`src/test/setup.ts` resets between tests: unmount, reset Zustand stores, unstub
globals. Add each new Zustand store to that reset — module-level singletons leak
state from one test into the next, and the resulting failure looks like a flake.
