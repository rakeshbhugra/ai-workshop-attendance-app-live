/**
 * The frontend test example.
 *
 * Tests behaviour through the DOM the way a user meets it — find things by role
 * and label, not by CSS class or component internals. A test written that way
 * survives a restyle and still fails when the feature actually breaks.
 *
 * `fetch` is stubbed rather than the hooks: that keeps the real Query cache,
 * real mutation flow and real error mapping in the test, so the wiring between
 * them is what's under test, not a mock of it.
 */

import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NotesPage } from "./notes-page";
import { mockFetchSequence, renderWithProviders } from "@/test/utils";
import type { Note } from "./types";

function note(overrides: Partial<Note> = {}): Note {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Groceries",
    body: "milk",
    created_at: "2026-01-01T12:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
    archived_at: null,
    is_archived: false,
    ...overrides,
  };
}

describe("NotesPage", () => {
  it("renders the notes returned by the API", async () => {
    mockFetchSequence([{ body: [note()] }]);

    renderWithProviders(<NotesPage />);

    expect(await screen.findByText("Groceries")).toBeInTheDocument();
  });

  it("shows an empty state when there are no notes", async () => {
    mockFetchSequence([{ body: [] }]);

    renderWithProviders(<NotesPage />);

    expect(await screen.findByText(/no notes yet/i)).toBeInTheDocument();
  });

  it("disables the submit button until a title is typed", async () => {
    mockFetchSequence([{ body: [] }]);
    const user = userEvent.setup();

    renderWithProviders(<NotesPage />);
    const button = screen.getByRole("button", { name: /add note/i });
    expect(button).toBeDisabled();

    await user.type(screen.getByLabelText(/note title/i), "Buy milk");

    expect(button).toBeEnabled();
  });

  it("posts a new note and clears the input", async () => {
    const { calls } = mockFetchSequence([
      { body: [] }, // initial list
      { status: 201, body: note({ title: "Buy milk" }) }, // create
      { body: [note({ title: "Buy milk" })] }, // refetch after invalidation
    ]);
    const user = userEvent.setup();

    renderWithProviders(<NotesPage />);
    const input = await screen.findByLabelText(/note title/i);
    await user.type(input, "Buy milk");
    await user.click(screen.getByRole("button", { name: /add note/i }));

    await waitFor(() => expect(input).toHaveValue(""));
    const post = calls.find((c) => c.init?.method === "POST");
    expect(post?.url).toBe("/api/v1/notes");
    expect(JSON.parse(String(post?.init?.body))).toEqual({ title: "Buy milk", body: "" });
  });

  it("surfaces a business-rule rejection to the user verbatim", async () => {
    mockFetchSequence([
      { body: [] },
      { status: 422, body: { detail: "A note title cannot be blank." } },
    ]);
    const user = userEvent.setup();

    renderWithProviders(<NotesPage />);
    await user.type(await screen.findByLabelText(/note title/i), "   x");
    await user.click(screen.getByRole("button", { name: /add note/i }));

    // 422 is user-fixable, so the server's own wording is shown rather than a
    // generic "something went wrong".
    expect(await screen.findByText("A note title cannot be blank.")).toBeInTheDocument();
  });

  it("hides the server's message for a 500, which the user cannot act on", async () => {
    mockFetchSequence([{ body: [] }, { status: 500, body: { detail: "psycopg2.OperationalError" } }]);
    const user = userEvent.setup();

    renderWithProviders(<NotesPage />);
    await user.type(await screen.findByLabelText(/note title/i), "Buy milk");
    await user.click(screen.getByRole("button", { name: /add note/i }));

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.queryByText(/OperationalError/)).not.toBeInTheDocument();
  });

  it("requests archived notes when the filter is toggled", async () => {
    const { calls } = mockFetchSequence([{ body: [] }]);
    const user = userEvent.setup();

    renderWithProviders(<NotesPage />);
    await user.click(await screen.findByLabelText(/show archived/i));

    await waitFor(() =>
      expect(calls.some((c) => c.url.includes("include_archived=true"))).toBe(true),
    );
  });
});
