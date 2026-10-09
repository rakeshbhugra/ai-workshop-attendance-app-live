/**
 * TanStack Query hooks — this app's **server state**.
 *
 * The division of labour, which is the single most important frontend
 * convention in this template:
 *
 *   TanStack Query  →  anything that lives on the server. Notes, users,
 *                      settings. It is fetched, cached, invalidated and can go
 *                      stale. You never copy it into another store.
 *   Zustand         →  anything that only exists in this browser tab. Which
 *                      modal is open, the current filter, an unsaved draft.
 *
 * The failure mode this prevents: fetching notes with Query and then copying
 * them into a Zustand store "so components can read them". Now there are two
 * sources of truth, they disagree after a mutation, and every bug is a cache
 * bug. If it came from the server, read it from Query.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { noteKeys, notesApi } from "./api";
import type { Note, NoteCreate, NoteUpdate } from "./types";

export function useNotes(includeArchived: boolean) {
  return useQuery({
    queryKey: noteKeys.list(includeArchived),
    queryFn: () => notesApi.list(includeArchived),
  });
}

export function useNote(id: string) {
  return useQuery({
    queryKey: noteKeys.detail(id),
    queryFn: () => notesApi.get(id),
    enabled: Boolean(id),
  });
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NoteCreate) => notesApi.create(payload),
    // Invalidate rather than manually pushing the new note into the cached
    // array: the server may have normalised the title, and a refetch is the
    // only thing guaranteed to agree with it.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: noteKeys.lists() }),
  });
}

export function useUpdateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: NoteUpdate }) =>
      notesApi.update(id, payload),
    onSuccess: (updated: Note) => {
      // The server already returned the new state, so seed the detail cache
      // with it (no refetch needed) and mark the lists stale.
      queryClient.setQueryData(noteKeys.detail(updated.id), updated);
      void queryClient.invalidateQueries({ queryKey: noteKeys.lists() });
    },
  });
}

export function useArchiveNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      archived ? notesApi.restore(id) : notesApi.archive(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: noteKeys.all }),
  });
}

export function useDeleteNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notesApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: noteKeys.all }),
  });
}
