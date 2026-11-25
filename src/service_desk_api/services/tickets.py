"""Business rules for ticket visibility, lifecycle and audit history."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from service_desk_api.models.ticket import (
    Ticket,
    TicketComment,
    TicketEvent,
    TicketPriority,
    TicketStatus,
)
from service_desk_api.models.user import User, UserRole


class TicketNotFoundError(Exception):
    """Ticket does not exist or is not visible to the caller."""


class TicketRuleError(Exception):
    """A requested ticket operation violates a business rule."""


def _visible_ticket(db: Session, ticket_id: UUID, actor: User) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or (
        actor.role == UserRole.REQUESTER and ticket.requester_id != actor.id
    ) or (
        actor.role == UserRole.AGENT and ticket.assigned_to_id not in (None, actor.id)
    ):
        raise TicketNotFoundError
    return ticket


def _record_event(db: Session, ticket: Ticket, actor: User, event_type: str, details: str) -> None:
    db.add(TicketEvent(
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type=event_type,
        details=details,
    ))


def create_ticket(
    db: Session, actor: User, *, title: str, description: str, priority: TicketPriority
) -> Ticket:
    ticket = Ticket(
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        requester_id=actor.id,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.flush()
    _record_event(db, ticket, actor, "created", "Ticket created")
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    actor: User,
    *,
    page: int = 1,
    page_size: int = 20,
    ticket_status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
) -> tuple[list[Ticket], int]:
    filters = []
    if actor.role == UserRole.REQUESTER:
        filters.append(Ticket.requester_id == actor.id)
    elif actor.role == UserRole.AGENT:
        filters.append(
            (Ticket.assigned_to_id == actor.id) | (Ticket.assigned_to_id.is_(None))
        )
    if ticket_status is not None:
        filters.append(Ticket.status == ticket_status)
    if priority is not None:
        filters.append(Ticket.priority == priority)

    count_statement = select(func.count()).select_from(Ticket).where(*filters)
    total = db.scalar(count_statement) or 0
    statement = (
        select(Ticket)
        .where(*filters)
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all()), total


def get_ticket_detail(
    db: Session, ticket_id: UUID, actor: User
) -> tuple[Ticket, list[TicketComment], list[TicketEvent]]:
    ticket = _visible_ticket(db, ticket_id, actor)
    comments = list(db.scalars(
        select(TicketComment).where(TicketComment.ticket_id == ticket.id)
        .order_by(TicketComment.created_at.asc())
    ).all())
    events = list(db.scalars(
        select(TicketEvent).where(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.created_at.asc())
    ).all())
    return ticket, comments, events


def add_comment(db: Session, ticket_id: UUID, actor: User, body: str) -> TicketComment:
    ticket = _visible_ticket(db, ticket_id, actor)
    if ticket.status == TicketStatus.CLOSED:
        raise TicketRuleError("Closed tickets cannot receive comments")
    comment = TicketComment(ticket_id=ticket.id, author_id=actor.id, body=body.strip())
    db.add(comment)
    _record_event(db, ticket, actor, "commented", "A comment was added")
    db.commit()
    db.refresh(comment)
    return comment


def assign_ticket(db: Session, ticket_id: UUID, actor: User, agent_id: UUID) -> Ticket:
    ticket = _visible_ticket(db, ticket_id, actor)
    agent = db.get(User, agent_id)
    if agent is None or not agent.is_active or agent.role not in (
        UserRole.AGENT, UserRole.ADMINISTRATOR
    ):
        raise TicketRuleError("Assignee must be an active support agent")
    ticket.assigned_to_id = agent.id
    _record_event(db, ticket, actor, "assigned", f"Assigned to {agent.id}")
    db.commit()
    db.refresh(ticket)
    return ticket


def change_ticket_status(
    db: Session, ticket_id: UUID, actor: User, new_status: TicketStatus
) -> Ticket:
    ticket = _visible_ticket(db, ticket_id, actor)
    allowed = {
        TicketStatus.OPEN: {TicketStatus.IN_PROGRESS},
        TicketStatus.IN_PROGRESS: {
            TicketStatus.WAITING_FOR_REQUESTER, TicketStatus.RESOLVED
        },
        TicketStatus.WAITING_FOR_REQUESTER: {TicketStatus.IN_PROGRESS},
        TicketStatus.RESOLVED: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
        TicketStatus.CLOSED: set(),
    }
    if new_status not in allowed[ticket.status]:
        raise TicketRuleError(
            f"Transition from {ticket.status.value} to {new_status.value} is not allowed"
        )
    if actor.role == UserRole.REQUESTER and not (
        ticket.status == TicketStatus.RESOLVED and new_status == TicketStatus.CLOSED
    ):
        raise TicketRuleError("Requesters may only close resolved tickets")
    if actor.role == UserRole.AGENT and ticket.assigned_to_id not in (None, actor.id):
        raise TicketNotFoundError
    previous = ticket.status
    ticket.status = new_status
    _record_event(db, ticket, actor, "status_changed", f"{previous.value} -> {new_status.value}")
    db.commit()
    db.refresh(ticket)
    return ticket
