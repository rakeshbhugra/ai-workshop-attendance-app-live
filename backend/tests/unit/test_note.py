"""Domain tests — the base of the pyramid.

No database, no fixtures, no async, no app. Just a class and its rules. These run
in single-digit milliseconds, which is why there should be *lots* of them: every
business rule you can push down into the domain becomes cheap to test here
instead of expensive to test through HTTP.

If this file is short and your e2e file is long, the business logic is in the
wrong layer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from attendance.domain.note import (
    TITLE_MAX_LENGTH,
    ArchivedNoteIsReadOnly,
    BlankNoteTitle,
    Note,
    NoteAlreadyArchived,
    NoteTitleTooLong,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)


def test_create_sets_both_timestamps_to_the_given_moment():
    note = Note.create(title="Groceries", body="milk", now=NOW)

    assert note.created_at == NOW
    assert note.updated_at == NOW
    assert note.archived_at is None
    assert not note.is_archived


def test_create_trims_surrounding_whitespace():
    note = Note.create(title="  Groceries  ", body="", now=NOW)

    assert note.title == "Groceries"


@pytest.mark.parametrize("title", ["", "   ", "\n\t"])
def test_a_title_that_is_blank_once_trimmed_is_rejected(title):
    with pytest.raises(BlankNoteTitle):
        Note.create(title=title, body="", now=NOW)


def test_a_title_over_the_limit_is_rejected():
    with pytest.raises(NoteTitleTooLong):
        Note.create(title="x" * (TITLE_MAX_LENGTH + 1), body="", now=NOW)


def test_editing_moves_updated_at_but_not_created_at():
    note = Note.create(title="Groceries", body="milk", now=NOW)

    note.edit(title="Shopping", body="milk, eggs", now=LATER)

    assert (note.title, note.body) == ("Shopping", "milk, eggs")
    assert note.created_at == NOW
    assert note.updated_at == LATER


def test_archiving_marks_the_note_and_stamps_the_time():
    note = Note.create(title="Groceries", body="", now=NOW)

    note.archive(now=LATER)

    assert note.is_archived
    assert note.archived_at == LATER


def test_archiving_twice_is_an_error_because_it_would_lose_the_first_timestamp():
    note = Note.create(title="Groceries", body="", now=NOW)
    note.archive(now=NOW)

    with pytest.raises(NoteAlreadyArchived):
        note.archive(now=LATER)

    assert note.archived_at == NOW


def test_an_archived_note_cannot_be_edited():
    note = Note.create(title="Groceries", body="milk", now=NOW)
    note.archive(now=NOW)

    with pytest.raises(ArchivedNoteIsReadOnly):
        note.edit(title="Shopping", body="eggs", now=LATER)

    assert note.title == "Groceries"  # the failed edit changed nothing


def test_restoring_an_archived_note_makes_it_editable_again():
    note = Note.create(title="Groceries", body="", now=NOW)
    note.archive(now=NOW)

    note.restore(now=LATER)

    assert not note.is_archived
    note.edit(title="Shopping", body="", now=LATER)  # no longer raises


def test_restoring_an_active_note_is_a_no_op_rather_than_an_error():
    note = Note.create(title="Groceries", body="", now=NOW)

    note.restore(now=LATER)

    assert not note.is_archived
    # The caller's intent ("make sure this is active") was already true, so
    # nothing was touched — including updated_at.
    assert note.updated_at == NOW
