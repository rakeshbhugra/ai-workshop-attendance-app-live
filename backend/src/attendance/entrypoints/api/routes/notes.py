"""HTTP entrypoint for notes.

Routes are **thin on purpose**: parse input, call one service method, shape the
response. There is no ``if``, no loop and no business vocabulary in this file. If
a route grows a decision, that decision belongs in a service or on an entity.

Nothing here catches domain errors either — ``exception_handlers.py`` maps them
to status codes once, for every route.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from attendance.bootstrap import get_note_service
from attendance.entrypoints.api.schemas.notes import NoteCreate, NoteResponse, NoteUpdate
from attendance.services.notes import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    include_archived: bool = Query(False),
    service: NoteService = Depends(get_note_service),
) -> list[NoteResponse]:
    notes = await service.list(include_archived=include_archived)
    return [NoteResponse.of(n) for n in notes]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    note = await service.create(title=payload.title, body=payload.body)
    return NoteResponse.of(note)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: uuid.UUID,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    return NoteResponse.of(await service.get(note_id))


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    note = await service.edit(note_id, title=payload.title, body=payload.body)
    return NoteResponse.of(note)


@router.post("/{note_id}/archive", response_model=NoteResponse)
async def archive_note(
    note_id: uuid.UUID,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    return NoteResponse.of(await service.archive(note_id))


@router.post("/{note_id}/restore", response_model=NoteResponse)
async def restore_note(
    note_id: uuid.UUID,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    return NoteResponse.of(await service.restore(note_id))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    service: NoteService = Depends(get_note_service),
) -> None:
    await service.delete(note_id)
