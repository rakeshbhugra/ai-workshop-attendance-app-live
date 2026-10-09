# Adding a feature

The working recipe. It follows the shipped **Notes** feature end to end — every
step names the real file you can open and copy.

Worked example throughout: adding **Orders** to the app.

---

## The files a feature touches

```
backend/src/attendance/
  domain/order.py                          1. entity + rules
  ports/repositories.py                    2. OrderRepository (ABC)
  adapters/orm/tables.py                   3. order_table + mapping
  adapters/repositories/order.py           4. SqlAlchemyOrderRepository
  adapters/repositories/fakes.py           5. FakeOrderRepository
  ports/unit_of_work.py                    6. declare `orders`
  adapters/unit_of_work.py                 6. wire the real one
  adapters/unit_of_work_fake.py            6. wire the fake
  services/orders.py                       7. use cases
  entrypoints/api/schemas/orders.py        8. wire shapes
  entrypoints/api/routes/orders.py         9. HTTP
  entrypoints/api/router.py                9. register the router
  bootstrap.py                            10. get_order_service
backend/tests/
  unit/test_order.py                      11. rules
  service/test_orders.py                  11. use cases
  integration/test_order_repository.py    11. the adapter
  e2e/test_orders_api.py                  11. HTTP
frontend/src/features/orders/
  types.ts  api.ts  hooks.ts  OrdersPage.tsx  OrdersPage.test.tsx    12.
```

Work outward, domain first. Each step is testable before you start the next, so
you are never debugging four layers at once.

---

## 1. The entity

`domain/order.py`. A plain dataclass with the rules on it. Copy the shape of
[`domain/note.py`](../backend/src/attendance/domain/note.py).

```python
@dataclass
class Order:
    customer_id: uuid.UUID
    total: Decimal
    created_at: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    cancelled_at: datetime | None = None

    @classmethod
    def create(cls, customer_id, total, now) -> Order:
        if total <= 0:
            raise InvalidOrderTotal
        return cls(customer_id=customer_id, total=total, created_at=now)

    def cancel(self, now: datetime) -> None:
        if self.cancelled_at is not None:
            raise OrderAlreadyCancelled
        self.cancelled_at = now
```

Checklist:

- [ ] No imports of SQLAlchemy, Pydantic, FastAPI or any SDK.
- [ ] A `create()` classmethod, so an invalid instance cannot exist.
- [ ] `now` passed in, never `datetime.now()` inside.
- [ ] Errors subclass `NotFoundError` / `ConflictError` / `ValidationError` from
      `domain/exceptions.py` — that is what gets them the right HTTP status.

**Write the unit tests now** (`tests/unit/test_order.py`). No fixtures, no async,
no database. This is the cheapest tier and where most of your tests should live.

## 2. The port

Add `OrderRepository(ABC)` to `ports/repositories.py`. Collection vocabulary —
`add`, `get`, `list` — and one repository per aggregate root, not per table.
Document the contract (ordering, what `None` means) in the docstring; both
implementations are held to it.

## 3. The table

Add `order_table` to `adapters/orm/tables.py` and map it in
`adapters/orm/__init__.py::start_mappers`. Use `DateTime(timezone=True)` for
every timestamp.

Then generate the migration and **read it before committing**:

```bash
make migration m="add orders table"
```

Autogenerate is a good first draft, not a finished migration. It sees a rename as
a drop plus an add (which loses the data), it never writes a backfill, and it
does not know which index you actually need. Write the `downgrade()` too — you
will want it during a bad deploy, at which point it is too late to work out what
it should have said.

## 4–5. The adapters

`adapters/repositories/order.py` (SQLAlchemy) and `FakeOrderRepository` in
`adapters/repositories/fakes.py` (a dict).

The fake must obey the same contract as the real one. If `list()` is newest-first
in SQL, it is newest-first in the fake. When they drift, service tests go green
for the wrong reason — which is exactly what the integration tests in step 11
are there to catch.

## 6. The Unit of Work

Three files, same line in each:

```python
ports/unit_of_work.py         orders: OrderRepository
adapters/unit_of_work.py      self.orders = SqlAlchemyOrderRepository(session)
adapters/unit_of_work_fake.py self.orders = FakeOrderRepository()
```

Forgetting the fake is the usual slip; mypy catches it because both subclass the
same ABC.

## 7. The service

`services/orders.py`. One method per use case, each one `load → delegate → save`:

```python
async def cancel(self, order_id: uuid.UUID) -> Order:
    async with self._uow as uow:
        order = await self._require(uow, order_id)
        order.cancel(now=_now())       # the rule lives on the entity
        await uow.commit()             # always explicit
        return order
```

If you find yourself writing an `if` about the entity's state here, that rule
belongs back in step 1.

**Write the service tests now** (`tests/service/test_orders.py`), using
`FakeUnitOfWork`. Assert on the state the fake ends up in and on `uow.committed`
— never on which methods were called.

## 8–9. Schema and route

`schemas/orders.py` holds the wire shape. Use `UtcDatetime` (from
`schemas/common.py`) for every datetime — plain `datetime` will serialise
inconsistently between SQLite and Postgres and shift timestamps by the user's
timezone. Map explicitly with an `of()` classmethod rather than
`model_validate`, so a domain rename becomes a type error instead of a silently
changed API.

`routes/orders.py` stays thin — parse, call one service method, shape the
response. Do **not** catch domain errors; `exception_handlers.py` already maps
them. Register the router in `entrypoints/api/router.py`.

Schema validation vs domain validation: max length and required-ness go in the
schema (rejected at the edge with a good message); business rules like "total
must be positive" go in the domain, so they hold for every caller.

## 10. Wire it up

Add a `get_order_service` factory to `bootstrap.py`. This is the only file that
names concrete classes.

## 11. The remaining tests

Integration (does the real adapter behave like the fake?) and e2e (status codes,
URLs, serialisation). A handful of each. See [testing.md](testing.md).

## 12. The frontend

Copy `features/notes/`:

- **`types.ts`** — mirrors the Pydantic schema.
- **`api.ts`** — transport functions plus a `queryKeys` hierarchy. Keys in one
  place is what makes invalidation precise.
- **`hooks.ts`** — Query for reads, mutations for writes, invalidate on success.
- **`OrdersPage.tsx`** — handle loading, error *and* empty states explicitly; a
  real app spends real time in all three.

Server data lives in Query. Only tab-local state (open modals, filters) goes in
Zustand. Never copy one into the other.

Add the route in `main.tsx`.

---

## Before you push

```bash
make check     # lint, typecheck, dependency rule, backend + frontend tests
```

The dependency-rule check will tell you, with a file and line number, if a
service reached for an adapter.

---

## Deleting the example

Once you have a real feature, the Notes example has done its job:

```bash
git rm backend/src/attendance/domain/note.py \
       backend/src/attendance/adapters/repositories/note.py \
       backend/src/attendance/services/notes.py \
       backend/src/attendance/entrypoints/api/routes/notes.py \
       backend/src/attendance/entrypoints/api/schemas/notes.py \
       backend/tests/unit/test_note.py \
       backend/tests/service/test_notes.py \
       backend/tests/integration/test_note_repository.py \
       backend/tests/e2e/test_notes_api.py
git rm -r frontend/src/features/notes
```

Then remove `NoteRepository` from `ports/repositories.py`, the `notes` line from
the three Unit of Work files, `note_table` from `adapters/orm/`, `get_note_service`
from `bootstrap.py`, the router line, the route in `main.tsx`, and the initial
Alembic migration if you have not deployed yet.

Keep `files.py` / `ObjectStorage` if you need uploads; it is the reference for
every non-database adapter you add later. Otherwise delete it the same way.
