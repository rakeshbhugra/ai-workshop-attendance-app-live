# Blocks

The plan for auth, RBAC and everything else that gets reused between apps:
each capability is a **block** — a port, its adapters, and the wiring — that you
copy in and configure, rather than a framework you inherit from.

The template ships with two blocks already built (**object storage** and **auth**) so the shape
is concrete rather than aspirational.

---

## Why this shape

Every external system the app talks to enters through the same door:

```
ports/<capability>.py              the interface — what the app needs
adapters/<capability>/real.py      the production implementation
adapters/<capability>/fake.py      the test implementation
bootstrap.py                       picks one, based on config
```

Because services depend on the port, a block is genuinely detachable. Adding
another sign-in provider to an app that had none means adding an adapter and one line in
`bootstrap.py` — no service changes, no route changes, and the tests keep running
without an identity provider.

This is not a new idea, it is [the architecture](architecture.md) applied
consistently. A repository is a block for the database. Auth is a block for
identity. Same shape, different hole.

---

## The reference block: object storage

Read these five files in order — they are the template for every block that comes
after.

| File | Role |
|---|---|
| [`ports/object_storage.py`](../backend/src/attendance/ports/object_storage.py) | the interface: `put`, `get`, `delete` |
| [`adapters/storage/s3.py`](../backend/src/attendance/adapters/storage/s3.py) | real S3 / LocalStack |
| [`adapters/storage/in_memory.py`](../backend/src/attendance/adapters/storage/in_memory.py) | the fake — and the zero-config default |
| [`adapters/storage/__init__.py`](../backend/src/attendance/adapters/storage/__init__.py) | `build_object_storage(settings)` picks one |
| [`services/files.py`](../backend/src/attendance/services/files.py) | a service using the port, with no idea which |

Note what that buys: the file tests run with no bucket, no credentials and no
container, and `make up-aws` swaps in LocalStack without touching a line of
application code.

---

## Writing a block

1. **Define the port in the app's vocabulary, not the vendor's.** `AuthProvider.
   verify_token(token) -> Identity`, not `ClerkClient.get_session_claims()`. If
   the vendor's nouns leak into the port, swapping the vendor changes every
   caller and the port earned nothing.
2. **Keep it small.** Only the methods the app actually calls. A port mirroring
   the whole SDK is just the SDK with extra steps.
3. **Ship a fake with it.** A block without a fake makes every test that touches
   it require the real service. The fake is what makes the block adoptable.
4. **Configure through `Settings`.** Empty config means off, with a sane no-op
   fallback where that is safe — that is what keeps a fresh clone runnable.
5. **Return domain types.** The port returns an `Identity` the domain understands,
   not a vendor SDK response object.

### The rent test

Before adding a port, answer: **can you name a real second implementation?**

A fake for tests counts. A vendor you are actually likely to switch to counts.
"We might swap this someday" does not — that is a speculative abstraction, paying
indirection now for a future that usually never arrives. When there is exactly one
implementation and no test double, call the library directly and add the port when
the second case actually shows up.

---

## Planned blocks

Not built yet. Listed so the shape is settled before one gets written.

Auth is built: `ports/auth.py` (`IdentityProvider`, `SessionTokens`), adapters in
`adapters/auth/` (Google over OIDC, dev, fakes), `services/auth.py`, and
`routes/auth.py`. Another OIDC provider is one entry in `ISSUERS` plus two settings.

| Block | Port | Adapters | Notes |
|---|---|---|---|
| **RBAC** | `PermissionPolicy.allows(identity, action, resource) -> bool` | database-backed, static-config | Enforce in **services**, not routes — a rule enforced only at the HTTP edge is not enforced for a CLI or a worker |
| **Notifications** | `Notifier.send(to, message)` | Slack, email, fake | |
| **LLM** | `Completer.complete(prompt) -> Completion` | LiteLLM, fake | Keep prompts out of the domain |
| **Background jobs** | `JobQueue.enqueue(job)` | SQS (LocalStack locally), in-process fake | The `aws` compose profile already runs SQS |

### Where RBAC gets enforced

The one decision worth settling now, because it is expensive to move later.

Authorisation belongs in the **service**, at the top of the use case — not in the
route decorator. A route-level check is invisible to every other entrypoint: the
moment the same use case is reachable from a CLI command, a scheduled job or an
MCP tool, the rule silently stops applying. Services are the layer every
entrypoint goes through, so a check there holds for all of them.

The identity itself is resolved at the edge (a `Depends` reading the session
cookie) and passed *into* the service as an argument. The service takes an
`Identity`, not a `Request`.

---

## Adding a block to an existing app

1. Copy `ports/<capability>.py` and `adapters/<capability>/`.
2. Add its settings to `config/settings.py`.
3. Add the builder call and the `Depends` factory to `bootstrap.py`.
4. Add the env vars to `.env.example` and to both compose files.
5. Take the service tests with it — they run against the fake and need nothing.

If a step needs a change to an existing service, the port is wrong: it is
exposing the vendor rather than the capability. Fix the port before continuing.
