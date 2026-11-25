"""Ticket workflow endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from service_desk_api.api.dependencies import get_current_user, require_roles
from service_desk_api.database import get_db
from service_desk_api.models.ticket import Ticket
from service_desk_api.models.user import User, UserRole
from service_desk_api.schemas.ticket import (
    TicketAssign,
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketDetail,
    TicketPage,
    TicketPriority,
    TicketRead,
    TicketStatus,
    TicketStatusUpdate,
)
from service_desk_api.services.tickets import (
    TicketNotFoundError,
    TicketRuleError,
    add_comment,
    assign_ticket,
    change_ticket_status,
    create_ticket,
    get_ticket_detail,
    list_tickets,
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Ticket not found")


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: TicketCreate,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Ticket:
    return create_ticket(
        db, actor, title=payload.title, description=payload.description, priority=payload.priority
    )


@router.get("", response_model=TicketPage)
def list_mine(
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ticket_status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
) -> TicketPage:
    items, total = list_tickets(
        db,
        actor,
        page=page,
        page_size=page_size,
        ticket_status=ticket_status,
        priority=priority,
    )
    return TicketPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketDetail)
def detail(
    ticket_id: UUID,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketDetail:
    try:
        ticket, comments, events = get_ticket_detail(db, ticket_id, actor)
    except TicketNotFoundError:
        raise _not_found() from None
    return TicketDetail.model_validate({
        **TicketRead.model_validate(ticket).model_dump(),
        "comments": comments,
        "events": events,
    })


@router.post("/{ticket_id}/comments", response_model=TicketCommentRead, status_code=201)
def comment(
    ticket_id: UUID,
    payload: TicketCommentCreate,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return add_comment(db, ticket_id, actor, payload.body)
    except TicketNotFoundError:
        raise _not_found() from None
    except TicketRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.patch("/{ticket_id}/assignment", response_model=TicketRead)
def assign(
    ticket_id: UUID,
    payload: TicketAssign,
    actor: Annotated[User, Depends(require_roles(UserRole.ADMINISTRATOR))],
    db: Annotated[Session, Depends(get_db)],
) -> Ticket:
    try:
        return assign_ticket(db, ticket_id, actor, payload.agent_id)
    except TicketNotFoundError:
        raise _not_found() from None
    except TicketRuleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_status(
    ticket_id: UUID,
    payload: TicketStatusUpdate,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Ticket:
    try:
        return change_ticket_status(db, ticket_id, actor, payload.status)
    except TicketNotFoundError:
        raise _not_found() from None
    except TicketRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
