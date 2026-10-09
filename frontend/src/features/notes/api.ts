/**
 * Transport functions for notes — plain async functions, no React.
 *
 * Kept separate from the hooks so they can be called from anywhere (a route
 * loader, a test, a script) and so the hooks file stays about caching rather
 * than about URLs.
 */

import { api } from "@/lib/api";
import type { Note, NoteCreate, NoteUpdate } from "./types";

export const notesApi = {
  list: (includeArchived: boolean) =>
    api.get<Note[]>(`/notes?include_archived=${includeArchived}`),
  get: (id: string) => api.get<Note>(`/notes/${id}`),
  create: (payload: NoteCreate) => api.post<Note>("/notes", payload),
  update: (id: string, payload: NoteUpdate) => api.put<Note>(`/notes/${id}`, payload),
  archive: (id: string) => api.post<Note>(`/notes/${id}/archive`),
  restore: (id: string) => api.post<Note>(`/notes/${id}/restore`),
  remove: (id: string) => api.delete(`/notes/${id}`),
};

/**
 * Query keys in one place, built as a hierarchy.
 *
 * The hierarchy is what makes invalidation precise: invalidating
 * `noteKeys.lists()` refetches every list variant (archived or not) without
 * touching cached detail views, and `noteKeys.all` nukes everything. Scattering
 * raw string keys across components is how caches end up stale in one corner of
 * the app and over-fetching in another.
 */
export const noteKeys = {
  all: ["notes"] as const,
  lists: () => [...noteKeys.all, "list"] as const,
  list: (includeArchived: boolean) => [...noteKeys.lists(), { includeArchived }] as const,
  details: () => [...noteKeys.all, "detail"] as const,
  detail: (id: string) => [...noteKeys.details(), id] as const,
};
