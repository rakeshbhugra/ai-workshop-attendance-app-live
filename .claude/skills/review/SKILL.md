---
name: review
description: Review changed code against this repo's guidelines: layering and the dependency rule, domain richness, the TanStack Query / Zustand split, file length, tests, async safety, N+1 queries, migrations and logging. Use when asked to review code, check a diff or a PR before pushing, or verify a change follows the project's conventions.
---

# Code review

Review the changes against this repo's guidelines. Report what is **wrong**, not
what is fine.

## Step 1 — run the mechanical checks first

Do not spend reasoning on anything a script already decides. Run:

```bash
make lint     # ruff, mypy --strict, tsc, dependency rule, file length
make test     # backend (4 tiers) + frontend
```

If these fail, report the failures and stop — there is no point reviewing style
in code that does not typecheck. If they pass, **do not re-report anything they
cover**: import order, formatting, type errors, a service importing an adapter,
a file over 250 code lines. Those are settled.

Then get the diff. Default to the branch:

```bash
git diff main...HEAD        # or: git diff --staged, or a named range
```

Review **only what changed**, plus whatever you must read to judge it. A review
that wanders into untouched files is noise.

## Step 2 — load the guidelines you need

Read only what the diff touches:

| Diff touches | Read |
|---|---|
| `backend/src/**` | `docs/backend.md`, `docs/architecture.md` |
| `frontend/src/**` | `docs/frontend.md` |
| tests | `docs/testing.md` |
| repositories, list endpoints, loops with awaits | `docs/performance.md` |
| `adapters/orm/`, `alembic/` | `docs/backend.md` (database section) |

These files are the standard. Quote the specific rule rather than re-deriving
the reasoning — and if the code contradicts a doc, say which doc.

## Step 3 — check what scripts cannot

This is where the value is. In rough priority order:

### Correctness and safety
- **N+1 queries** — an `await` on a query inside a loop over rows. Invisible
  locally, a 15-second request in production. The most common real bug in this
  codebase's shape.
- **Blocking calls in `async def`** — `requests`, `time.sleep`, a sync SDK.
  Stalls the whole event loop, not just that request. Should be
  `asyncio.to_thread`.
- **A write path with no `await uow.commit()`**, or a commit inside a loop.
- **Secrets, tokens, request bodies or personal data in a log line.**
- **Unvalidated input used as a path, key or query fragment.**
- **A migration that drops or renames a column** — autogenerate writes rename as
  drop+add, which loses data. Check for a backfill and a real `downgrade()`.
- **An index or constraint added only in a migration**, not in
  `adapters/orm/tables.py` — the next autogenerate will drop it.

### Layering (the parts `check_dependency_rule.py` cannot see)
- **A business rule that drifted into a service** — `if entity.state == ...:
  raise` belongs on the entity, or the next caller will forget it.
- **An anemic entity** — a dataclass with no behaviour plus a service full of
  procedure is this architecture's folders without its benefit.
- **A fat route** — an `if`, a loop, or business vocabulary in an entrypoint.
- **A service taking a session or a concrete repository** instead of a port.
- **HTTP vocabulary in a service** (`HTTPException`, status codes).
- **A domain error caught in a route** instead of mapped centrally.
- **A new port with only one implementation and no fake** — apply the rent test:
  can you name a real second implementation? If not, it is speculative.

### Frontend
- **Server data copied into Zustand** — the cardinal error. Two sources of truth
  that disagree after the first mutation.
- **A query key written inline** instead of in the feature's key hierarchy.
- **A mutation that doesn't invalidate**, or hand-patches the list cache.
- **Missing loading / error / empty states.**
- **Subscribing to a whole Zustand store** (`const { x } = useStore()`) rather
  than selecting a slice — re-renders on every unrelated change.
- **A new Zustand store not reset in `src/test/setup.ts`** — causes
  order-dependent test failures.
- **`useEffect` doing what a plain expression or a query should do.**
- **Array index as a React `key`.**
- **An icon-only button with no accessible name** — also means tests can't find it.

### Tests
- **A new rule with no test at the cheapest tier.** A domain rule tested only
  through HTTP is slow and fragile.
- **The same rule asserted at three tiers** — triples the cost of changing it.
- **Assertions on which methods were called** (mock-style) rather than resulting
  state.
- **A fake whose contract drifted from the real adapter** — ordering, `None`
  semantics. Green tests for the wrong reason.
- **A test asserting behaviour the change didn't alter**, or one that cannot
  fail.

### Fit and clarity
- **Files over 150 code lines** (`make sizes`) — advisory, but say where the
  seam is: usually a list item, a form, or a hook lifted out of a page.
- **Comments explaining *what* instead of *why*.** The code says what.
- **A stale comment or doc** the change invalidated — especially `CLAUDE.md` and
  `docs/` when a convention moved.
- **Dead code, a commented-out block, a leftover `console.log` / `print`.**

## Step 4 — verify before reporting

For each candidate finding, try to disprove it. Read the surrounding code; check
whether a guard exists elsewhere; confirm the import is what you think. A
confident wrong finding costs more trust than a missed one.

Drop anything you could not confirm. If a finding is real but you are unsure of
the severity, say so.

## Output

Group by severity, most severe first. For each:

- **file:line** — one sentence on what is wrong
- **Why it matters** — the concrete consequence, not the rule name
- **The fix** — the shape of it, with a code sketch when that is clearer

```
## Must fix
backend/src/attendance/services/orders.py:42 — queries the customer inside the loop
over orders (N+1).
  Why: 200 orders becomes 201 round trips; ~15s in production, 20ms locally.
  Fix: add `get_many(ids)` to CustomerRepository and build a dict before the loop.

## Should fix
frontend/src/features/orders/orders-page.tsx:18 — copies `data` from useOrders()
into the Zustand store.
  Why: two sources of truth; they diverge after the first mutation.
  Fix: read from the hook directly; delete the store field and its useEffect.

## Consider
backend/src/attendance/services/orders.py — 190 code lines.
  Fix: `cancel`/`refund` are a cohesive pair; move them to `services/refunds.py`.
```

End with one line: what is good about the change, and whether it is safe to merge
once the "must fix" items are addressed.

## Rules for the reviewer

- **Be specific.** "Consider improving error handling" is not a review finding.
- **No praise padding.** A short review is a good outcome.
- **Match rigour to the change.** A one-line copy fix does not need an
  architecture assessment.
- **Don't invent work.** Speculative abstractions and hypothetical futures are
  things this repo explicitly rejects — don't ask for them in review.
- **Prefer deleting to adding.** If a finding can be fixed by removing code, say so.
