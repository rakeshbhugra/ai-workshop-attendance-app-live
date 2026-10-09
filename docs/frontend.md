# Frontend guidelines

React 19, TypeScript strict, Vite, Tailwind 4, **TanStack Query** for server
state, **Zustand** for client state.

The rules here are enforced three ways: `npx tsc -b --noEmit` in CI,
`scripts/check_file_length.py`, and the review skill (`/review`), which reads
this file.

---

## The one rule: two stores, never both

This is the decision people get wrong, and it is expensive to unwind.

| | |
|---|---|
| **TanStack Query** | anything the **server** owns. Notes, users, settings. Fetched, cached, invalidated, can be stale. |
| **Zustand** | anything only **this browser tab** knows. Open modals, filters, drafts, sidebar collapsed. |

**Never copy server data into Zustand.**

```ts
// ❌ two sources of truth. They agree until the first mutation, and then
//    every bug in this feature is a cache bug.
const { data } = useNotes();
useEffect(() => setNotesInStore(data), [data]);

// ✅ read it where it lives
const { data: notes } = useNotes();
```

If a component needs server data, it calls the hook. Query deduplicates
identical keys, so ten components calling `useNotes()` produce **one** request —
"I'll fetch it once at the top and pass it down" is solving a problem Query has
already solved, at the cost of prop-drilling.

**When you genuinely need both:** a filter (client) that changes what you fetch
(server). Keep them separate and let the filter feed the key:

```ts
const showArchived = useUiStore((s) => s.showArchived);   // client
const { data } = useNotes(showArchived);                  // server, re-keyed
```

Changing the filter changes the query key, so Query fetches (or serves a cached
result) automatically. No `useEffect`, no manual refetch.

---

## TanStack Query

### Query keys live in `api.ts`, as a hierarchy

```ts
export const noteKeys = {
  all: ["notes"] as const,
  lists: () => [...noteKeys.all, "list"] as const,
  list: (includeArchived: boolean) => [...noteKeys.lists(), { includeArchived }] as const,
  detail: (id: string) => [...noteKeys.all, "detail", id] as const,
};
```

The hierarchy is what makes invalidation precise. `invalidateQueries({ queryKey:
noteKeys.lists() })` refetches every list variant and leaves cached detail views
alone; `noteKeys.all` clears everything. Raw string keys scattered across
components are how a cache ends up stale in one corner and over-fetching in
another.

Never write a key inline in a component.

### Mutations invalidate; they don't hand-patch the cache

```ts
export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NoteCreate) => notesApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: noteKeys.lists() }),
  });
}
```

The server may have normalised the input, stamped a timestamp or applied a rule.
A refetch is the only thing guaranteed to agree with it. When the server returns
the updated object, seeding the *detail* cache with it is fine —
`setQueryData(noteKeys.detail(id), updated)` — but still invalidate the lists.

Reach for optimistic updates (`onMutate` + rollback) only where the latency is
genuinely felt: drag-and-drop, toggles, typing. Everywhere else the complexity
and the rollback paths are not worth it.

### Handle all four states

`isPending`, `isError`, empty, and data. A real app spends real time in the
first three, and skipping them is how "works on my machine" happens. See
`features/notes/notes-page.tsx`.

### Don't retry what won't change

Configured once in `main.tsx`: 4xx never retries, 5xx retries twice. Retrying a
404 just makes the user wait three times as long for the same answer.

---

## Zustand

Store per concern, in `src/stores/<name>-store.ts`. State and the actions that
change it live together:

```ts
export const useUiStore = create<UiState>((set) => ({
  showArchived: false,
  toggleShowArchived: () => set((s) => ({ showArchived: !s.showArchived })),
}));
```

**Always select the narrowest slice.** Subscribing to the whole store re-renders
the component on every unrelated change:

```ts
const showArchived = useUiStore((s) => s.showArchived);   // ✅
const { showArchived } = useUiStore();                    // ❌ re-renders on any change
```

Selecting a new object or array literal (`useUiStore((s) => ({ a: s.a }))`) also
re-renders every time, because the identity is new on each call. Select the
primitives separately, or use `useShallow`.

Stores are module-level singletons, so **every store must be reset between
tests** — add it to `src/test/setup.ts`. Skipping this produces failures that
depend on test order, which is the worst kind to debug.

---

## Files and structure

```
src/
  lib/api.ts                 the ONLY place that calls fetch
  features/<feature>/
    types.ts                 wire types, mirroring the Pydantic schema
    api.ts                   transport functions + query keys
    hooks.ts                 Query/mutation hooks
    <feature>-page.tsx       the page
    <thing>-card.tsx         components used only by this feature
    <feature>-page.test.tsx
  components/                shared across features only
  stores/<name>-store.ts
```

- **Filenames are kebab-case** (`notes-page.tsx`, `ui-store.ts`); the exported
  component stays PascalCase (`NotesPage`). Same convention as
  `orqestrator_admin_frontend`.
- **A component belongs to a feature until a second feature needs it.** Moving
  it to `components/` on the day it is genuinely shared is easy; untangling a
  premature "shared" component that grew three feature-specific props is not.
- **150 code lines is the guideline, 250 the hard limit** — comments and blank
  lines don't count, so explaining yourself is free. Over 150, the usual split is
  to lift the list item, the form, or a `use*` hook out of the page.

## Components

- **Handlers, loading and error states are the component's job. Business rules
  are not** — those live in the backend domain. A component deciding *whether*
  something is allowed is duplicating a rule that must hold for every client.
- **Derive during render, don't mirror in state.** `const visible =
  notes.filter(...)` beats a `useEffect` that writes to a `visibleNotes` state:
  one of them can go stale.
- **`useEffect` is for synchronising with something outside React** — a
  subscription, a timer, the DOM. Fetching is Query's job; transforming data is
  a plain expression's job. Most `useEffect`s in a codebase like this are a bug
  waiting to happen.
- **Keys must be stable ids**, never the array index — with an index, deleting
  an item makes React reuse the wrong DOM node and inputs keep the wrong values.

## Accessibility, briefly

Every interactive element needs an accessible name: visible text, or
`aria-label` for icon-only buttons. This is not only the right thing — it is what
makes the tests work, because they query by role and name. If a test cannot find
your button, a screen reader could not either.

## Errors

`lib/api.ts` throws `ApiError` with a `status`. Show the server's own message
only when the user can act on it (`isUserFixable` — 400/409/422); anything else
gets a generic message, because "psycopg2.OperationalError" helps nobody and
leaks internals.

---

## Testing

Vitest + Testing Library. Full detail in [testing.md](testing.md); the two rules
that matter most:

**Query by role and label, not CSS class.** Survives a restyle, fails when the
feature actually breaks, and doubles as an accessibility check.

**Stub `fetch`, not the hooks.** Keeps the real cache, the real mutation flow and
the real error mapping inside the test, so you are testing the wiring rather than
a mock of it.

## Debugging

React Query Devtools is mounted in dev (the icon in the corner) and shows every
query, its state and its data. When a screen shows stale or missing data, open
that before adding a `console.log` — it usually names the stale query outright.
It is stripped from production builds. See [debugging.md](debugging.md).
