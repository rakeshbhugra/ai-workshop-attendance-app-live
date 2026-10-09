"""Pydantic DTOs — the *wire* shape of a note.

Three kinds of "model" exist in this codebase and conflating them is the most
common subtle mistake:

* ``domain/note.py``        — the business entity (rules live here)
* ``adapters/orm/tables.py`` — the row shape (columns, indexes, FKs)
* this file                 — the wire shape (what JSON goes in and out)

They look similar today and will diverge tomorrow: the wire shape grows a
computed ``is_archived`` the table doesn't have, the table grows a
``search_vector`` the API never returns. Keeping them separate is what lets that
happen without a rewrite.

Validation split: shape/type rules (max length, required) go here so bad input is
rejected at the edge with a good error message. *Business* rules (a title cannot
be blank once trimmed) stay in the domain, because they must hold no matter which
entrypoint calls in.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from attendance.domain.note import TITLE_MAX_LENGTH, Note
from attendance.entrypoints.api.schemas.common import UtcDatetime


class NoteCreate(BaseModel):
    title: str = Field(max_length=TITLE_MAX_LENGTH)
    body: str = ""


class NoteUpdate(BaseModel):
    title: str = Field(max_length=TITLE_MAX_LENGTH)
    body: str = ""


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    # UtcDatetime, not datetime — see schemas/common.py for the timezone trap it
    # closes. Every datetime on the wire should use it.
    created_at: UtcDatetime
    updated_at: UtcDatetime
    archived_at: UtcDatetime | None
    is_archived: bool

    @classmethod
    def of(cls, note: Note) -> NoteResponse:
        """Explicit mapping rather than ``model_validate`` magic. It is three more
        lines and it means a domain rename can never silently change the API
        contract — the type checker points at this function instead."""
        return cls(
            id=note.id,
            title=note.title,
            body=note.body,
            created_at=note.created_at,
            updated_at=note.updated_at,
            archived_at=note.archived_at,
            is_archived=note.is_archived,
        )
