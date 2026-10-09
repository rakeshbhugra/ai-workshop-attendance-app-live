/**
 * The wire types, mirroring `entrypoints/api/schemas/notes.py`.
 *
 * Hand-written on purpose at this size — it is one small file and it stays
 * readable. Once the API surface grows past ~10 endpoints, generate this from
 * the backend's OpenAPI schema instead (`openapi-typescript`) and delete it;
 * hand-maintained types silently drift from the server, and a generated file
 * turns that drift into a compile error.
 */

export interface Note {
  id: string;
  title: string;
  body: string;
  /** ISO-8601, always UTC and always with an offset — see the backend's
   *  `UtcDatetime`. Safe to pass straight to `new Date()`. */
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  is_archived: boolean;
}

export interface NoteCreate {
  title: string;
  body: string;
}

export type NoteUpdate = NoteCreate;
