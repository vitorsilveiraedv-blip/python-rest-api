"""Request and response schemas for ticket workflows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from service_desk_api.models.ticket import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=10, max_length=10000)
    priority: TicketPriority = TicketPriority.NORMAL


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    requester_id: UUID
    assigned_to_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class TicketCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    author_id: UUID
    body: str
    created_at: datetime


class TicketAssign(BaseModel):
    agent_id: UUID


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    actor_id: UUID
    event_type: str
    details: str
    created_at: datetime


class TicketDetail(TicketRead):
    comments: list[TicketCommentRead]
    events: list[TicketEventRead]
