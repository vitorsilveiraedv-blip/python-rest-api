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

The implementation includes application configuration, database session lifecycle, versioned routing, health endpoints, authentication, role-based authorization, ticket lifecycle rules, comments and audit history. CI validates migrations and runs integration tests against PostgreSQL 16.

## Core domain model

- User: identity, password hash, active state and role.
- Team: support group responsible for handling requests.
- Ticket: requester, assignee, team, title, description, priority and status.
- TicketComment: message authored within a ticket.
- TicketEvent: append-only record of important ticket changes.

## Authorization model

- Requester: create tickets and read tickets they are allowed to access.
- Agent: work on tickets assigned to their team and add internal/public comments according to policy.
- Administrator: manage users, teams and system-wide settings.

Authorization must be enforced server-side for every resource operation. Hiding UI controls is not a security boundary.

## Ticket lifecycle

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

## Delivery status

### Foundation
- [x] Application factory, versioned API routing and health endpoints.
- [x] Docker and local PostgreSQL configuration.
- [x] Alembic migrations and PostgreSQL 16 migration validation in CI.

### Authentication and authorization
- [x] Requester registration and Argon2 password hashing.
- [x] Short-lived JWT access tokens with issuer, audience and expiry validation.
- [x] Role-based authorization and resource-level access checks.
- [x] Generic login errors and dummy Argon2 verification for unknown accounts.
- [x] Concurrent duplicate registration handled through the database uniqueness constraint.

### Ticket workflow
- [x] Ticket creation, listing, filtering and pagination.
- [x] Assignment and validated status transitions.
- [x] Comments and append-only audit events.
- [x] Requester, agent and administrator visibility rules.

### Remaining before public deployment
- [ ] Login rate limiting and abuse controls.
- [ ] Refresh-token rotation and revocation strategy.
- [ ] Security and dependency review.
- [ ] Deployment and operational verification in a real target environment.

## Explicit non-goals for the first release

- Microservices.
- Kubernetes.
- Distributed event streaming.
- Multi-region deployment.

These would add operational complexity without a demonstrated need for the initial product.
