/**
 * The worked example of a feature page.
 *
 * Read it for the four things every page in this codebase does:
 *   1. server data via a Query hook       — `useNotes`
 *   2. client-only state via Zustand      — `showArchived`, `notify`
 *   3. writes via a mutation hook         — `useCreateNote` et al
 *   4. explicit loading / error / empty states, because a real app spends real
 *      time in all three and skipping them is how "it works on my machine"
 *      happens.
 */

import { useState } from "react";
import { Archive, ArchiveRestore, Loader2, Trash2 } from "lucide-react";
import { ApiError } from "@/lib/api";
import { useUiStore } from "@/stores/ui-store";
import { useArchiveNote, useCreateNote, useDeleteNote, useNotes } from "./hooks";
import type { Note } from "./types";

export function NotesPage() {
  const showArchived = useUiStore((s) => s.showArchived);
  const toggleShowArchived = useUiStore((s) => s.toggleShowArchived);
  const notify = useUiStore((s) => s.notify);

  const { data: notes, isPending, isError, error } = useNotes(showArchived);
  const createNote = useCreateNote();
  const archiveNote = useArchiveNote();
  const deleteNote = useDeleteNote();

  const [title, setTitle] = useState("");

  function reportError(err: unknown) {
    // A 409/422 carries a message written for a human — show it. Anything else
    // is a bug or an outage, and its message would only confuse.
    const message =
      err instanceof ApiError && err.isUserFixable
        ? err.detail
        : "Something went wrong. Please try again.";
    notify(message, "error");
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    try {
      await createNote.mutateAsync({ title, body: "" });
      setTitle("");
      notify("Note created");
    } catch (err) {
      reportError(err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Notes</h1>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={toggleShowArchived}
            className="size-4 rounded border-slate-300"
          />
          Show archived
        </label>
      </div>

      <form onSubmit={handleCreate} className="flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What needs writing down?"
          aria-label="Note title"
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:focus:border-slate-300"
        />
        <button
          type="submit"
          // Disabled while in flight so a double-click can't create two notes.
          disabled={createNote.isPending || title.trim() === ""}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-40 dark:bg-slate-100 dark:text-slate-900"
        >
          {createNote.isPending ? "Adding…" : "Add note"}
        </button>
      </form>

      {isPending ? (
        <div className="flex items-center gap-2 py-12 text-sm text-slate-500">
          <Loader2 className="animate-spin" size={16} />
          Loading notes…
        </div>
      ) : isError ? (
        <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-900 dark:bg-red-950 dark:text-red-100">
          Could not load notes: {error.message}
        </p>
      ) : notes.length === 0 ? (
        <p className="py-12 text-center text-sm text-slate-500">
          No notes yet. Add one above.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
          {notes.map((note) => (
            <NoteRow
              key={note.id}
              note={note}
              onToggleArchive={() =>
                archiveNote.mutate(
                  { id: note.id, archived: note.is_archived },
                  { onError: reportError },
                )
              }
              onDelete={() => deleteNote.mutate(note.id, { onError: reportError })}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function NoteRow({
  note,
  onToggleArchive,
  onDelete,
}: {
  note: Note;
  onToggleArchive: () => void;
  onDelete: () => void;
}) {
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <span className={`flex-1 text-sm ${note.is_archived ? "text-slate-400 line-through" : ""}`}>
        {note.title}
      </span>
      <time
        dateTime={note.created_at}
        className="text-xs tabular-nums text-slate-400"
        // Always UTC on the wire; rendered in the viewer's locale.
        title={new Date(note.created_at).toLocaleString()}
      >
        {new Date(note.created_at).toLocaleDateString()}
      </time>
      <button
        onClick={onToggleArchive}
        aria-label={note.is_archived ? "Restore note" : "Archive note"}
        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
      >
        {note.is_archived ? <ArchiveRestore size={15} /> : <Archive size={15} />}
      </button>
      <button
        onClick={onDelete}
        aria-label="Delete note"
        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
      >
        <Trash2 size={15} />
      </button>
    </li>
  );
}
