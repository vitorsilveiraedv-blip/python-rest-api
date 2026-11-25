# Architecture and Technical Specification

## Product scope

Service Desk API is a backend for internal IT support operations. It will manage request intake, assignment, status transitions, communication and an auditable history of work.

The first release is an API-first modular monolith. This keeps deployment and local development simple while maintaining clear boundaries between transport, application services, domain rules and persistence.

## Proposed technology

- Python 3.12+
- FastAPI for HTTP routing and OpenAPI documentation
- Pydantic for request and response validation
- SQLAlchemy 2 for persistence
- PostgreSQL for relational data
- Alembic for schema migrations
- Pytest and HTTPX for automated tests
- Docker Compose for local infrastructure
- GitHub Actions for continuous integration

## Initial architecture

```text
HTTP Client
    |
FastAPI / API v1
    |
Application Services
    |
Domain Rules
    |
Repository / SQLAlchemy
    |
PostgreSQL
```

The initial implementation establishes application configuration, database session lifecycle, versioned routing, operational health endpoints and CI. Business modules will be added in later milestones.

## Core domain model (planned)

- User: identity, password hash, active state and role.
- Team: support group responsible for handling requests.
- Ticket: requester, assignee, team, title, description, priority and status.
- TicketComment: message authored within a ticket.
- TicketEvent: append-only record of important ticket changes.

## Authorization model (planned)

- Requester: create tickets and read tickets they are allowed to access.
- Agent: work on tickets assigned to their team and add internal/public comments according to policy.
- Administrator: manage users, teams and system-wide settings.

Authorization must be enforced server-side for every resource operation. Hiding UI controls is not a security boundary.

## Ticket lifecycle (planned)

```text
OPEN -> IN_PROGRESS -> WAITING_FOR_REQUESTER -> IN_PROGRESS
  |             |                         |
  +----------> RESOLVED <------------------+
                    |
                 CLOSED
```

Transitions will be validated in the domain layer. Invalid transitions must return a consistent client error and must not mutate data.

## Non-functional requirements

- Secrets are loaded from environment variables and never committed.
- Passwords are stored using a modern password-hashing algorithm, never plaintext.
- Authentication and authorization are tested independently.
- Database changes are versioned through migrations.
- Health endpoints distinguish process liveness from dependency readiness.
- API errors must not expose stack traces, credentials or database connection details.
- Automated tests cover normal behavior, invalid input, permissions and failure cases.
- Logs must avoid passwords, access tokens and sensitive ticket content.

## Acceptance criteria

### Foundation milestone
- [x] Application factory and versioned API routing.
- [x] Liveness endpoint does not require database availability.
- [x] Readiness endpoint checks database connectivity.
- [x] Docker and local PostgreSQL configuration.
- [x] CI runs lint and tests.
- [ ] CI run verified as successful.

### Authentication milestone
- [ ] User registration/invitation policy defined.
- [ ] Secure password hashing.
- [ ] Short-lived access tokens and refresh strategy.
- [ ] Role-based authorization tests.
- [ ] No secret or token leakage in logs.

### Ticket workflow milestone
- [ ] Ticket creation, listing, filtering and pagination.
- [ ] Assignment and validated status transitions.
- [ ] Comments and append-only audit events.
- [ ] Resource-level authorization tests.

### Release milestone
- [ ] Alembic migrations and documented migration workflow.
- [ ] API integration tests using PostgreSQL.
- [ ] Security and dependency review.
- [ ] Complete setup and API documentation.
- [ ] Deployment verified in a real target environment.

## Explicit non-goals for the first release

- Microservices.
- Kubernetes.
- Distributed event streaming.
- Multi-region deployment.

These would add operational complexity without a demonstrated need for the initial product.
