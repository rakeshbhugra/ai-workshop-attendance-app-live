# Performance and benchmarking

Five questions, five different tools. Reaching for the wrong one is why
performance work so often produces no improvement.

| Question | Tool | Command |
|---|---|---|
| Did this function get slower? | micro-benchmark | `make bench` |
| *Why* is this slow? | profiler | `py-spy` / `cProfile` |
| Does it hold up under load? | load test | `k6`, `locust` |
| Which query is slow? | `EXPLAIN ANALYZE` | psql |
| Is it slow in production? | traces + metrics | your APM |

**Measure before optimising.** Every engineer's intuition about which line is
slow is wrong often enough that guessing costs more time than measuring.

---

## The bug you will actually hit: N+1

In this shape of app, the overwhelming majority of "the page is slow" is a query
inside a loop.

```python
# ❌ 1 query for the list, then one per row. 200 notes = 201 round trips.
notes = await uow.notes.list()
for note in notes:
    note.author = await uow.people.get(note.author_id)

# ✅ two queries, regardless of how many notes there are
notes = await uow.notes.list()
authors = await uow.people.get_many({n.author_id for n in notes})
```

It is invisible locally — three rows, a database on localhost, 2ms. In
production, with 5,000 rows and a 3ms network hop, it is a 15-second request.

**How to catch it early:** turn on `ATTENDANCE_DB_ECHO=true` and exercise the
endpoint. If the same `SELECT` scrolls past with different parameters, that is an
N+1. Do this once for any endpoint that returns a list — it takes a minute and
catches the problem before a user does.

The repository is the right place to fix it: add a `get_many` / `map_for_*`
method that takes a set of ids and returns a dict.

---

## Micro-benchmarks

`tests/benchmark/`, run with `make bench`. In the normal suite they execute once
untimed, so the code cannot rot while adding no timing noise to CI.

They answer exactly one question: **did this get dramatically slower?** They do
not tell you whether the app is fast enough.

Benchmark things that scale with input size and sit on a request path. Do not
benchmark everything — each one can fail for unrelated reasons, and a suite full
of noisy benchmarks is one everybody learns to ignore.

Two cautions worth internalising:

- **Assert the benchmark measured the real thing.** A benchmark timing an empty
  list looks fast and proves nothing. Every benchmark here ends with an
  assertion for that reason.
- **Don't gate CI on absolute timings.** Shared runners vary by 2–3× between
  runs; a threshold tight enough to catch a real regression will fail randomly,
  and everyone will learn to re-run it. Compare locally with
  `--benchmark-compare` when you are actually optimising something.

## Profiling

When something *is* slow, find out where before changing anything.

```bash
# Sample a running process — works against the docker dev container, needs no
# code change, and safe enough to use in production.
py-spy top    --pid $(pgrep -f uvicorn)
py-spy record --pid $(pgrep -f uvicorn) -o profile.svg   # flame graph
```

A flame graph makes the answer obvious: the widest box is where the time goes.
Usually it is a query, a serialisation loop, or something blocking the event
loop.

## Load testing

Micro-benchmarks measure one function; load tests measure the system — the pool,
the queueing, the memory, the interaction between concurrent requests. They are
the only way to answer "will this hold up".

Test the shape of your real traffic, and watch p95/p99 rather than the mean.
Mean latency hides exactly the requests users complain about.

The four prod failure modes worth rehearsing: connection-pool exhaustion, memory
growth under sustained load, a slow dependency creating back-pressure, and a
retry storm amplifying a small outage.

## Database

`EXPLAIN ANALYZE` the query, not the ORM call. Look for `Seq Scan` on a large
table and for a row count wildly different from the estimate (stale statistics).

Index the query you actually run, not the column that looks important. The
template's `ix_notes_active_created_at` covers "not archived, newest first"
because that is the default list query. And declare indexes in
`adapters/orm/tables.py`, not only in the migration — see [backend.md](backend.md).

## Frontend

- **Bundle size:** `npm run build` prints it. Sourcemaps are on, so
  `npx vite-bundle-visualizer` will show what is big. A date library or an icon
  set imported wholesale is the usual culprit.
- **Re-renders:** select narrow slices from Zustand (see
  [frontend.md](frontend.md)). Reach for `memo`/`useMemo` after profiling with
  the React DevTools Profiler, not before — most of them cost more than they save.
- **Waterfalls:** independent queries should run in parallel, not chained
  through `enabled: !!previousResult`.

## When to do any of this

Not yet. Correct first, measured second, optimised third — and only where the
measurement pointed. The exception is N+1, which is worth avoiding by
construction because it is so predictable, and a load test before a launch you
cannot easily roll back.
