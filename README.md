# Service Desk API

A Python REST API for IT service desk operations, developed as a modular monolith with clear boundaries between HTTP delivery, application logic, domain rules and persistence.

> **Project status:** authentication and ticket workflow milestones implemented. The API supports requester registration, Argon2 password hashing, signed short-lived JWT access tokens, opaque rotating refresh tokens, session-family revocation, authenticated profile retrieval and role authorization dependencies. Ticket creation, visibility rules, assignment, lifecycle transitions, comments and audit history are implemented.

## Implemented capabilities
- FastAPI application factory and versioned API routing.
- Environment-driven settings with Pydantic Settings.
- SQLAlchemy 2 persistence models and request-scoped database sessions.
- Liveness and database-readiness health endpoints.
- Requester registration with normalized unique email addresses and database-safe handling of concurrent duplicate registrations.
- Argon2 password hashing; plaintext passwords are never stored.
- JWT access tokens validated for signature, issuer, audience, expiry and token type.
- Opaque refresh tokens stored only as SHA-256 hashes, rotated on use and revocable by session family.
- Persistent login rate limiting by hashed email and client IP.
- Authenticated `/auth/me` endpoint and role-based authorization.
- Ticket creation, role-aware listing, pagination, status/priority filters and detail visibility.
- Administrator-only assignment to active agents.
- Validated ticket lifecycle transitions and requester close-out of resolved tickets.
- Ticket comments and append-only audit event records.
- Generic authentication errors and dummy Argon2 verification for unknown emails to reduce timing-based account enumeration.
- Versioned Alembic migrations for users, tickets, comments and audit events, applied automatically by the local Compose API service and validated against PostgreSQL 16 in CI.
- Dockerfile and Docker Compose configuration for local PostgreSQL.
- Pytest integration tests against an isolated PostgreSQL 16 database, PostgreSQL migrations, and Ruff linting in GitHub Actions.

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health/live` | Process liveness |
| GET | `/api/v1/health/ready` | Database readiness |
| POST | `/api/v1/auth/register` | Register a requester |
| POST | `/api/v1/auth/login` | Obtain access and refresh tokens |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token |
| POST | `/api/v1/auth/logout` | Revoke a refresh-token session |
| GET | `/api/v1/auth/me` | Retrieve the authenticated profile |
| POST | `/api/v1/tickets` | Create a support ticket |
| GET | `/api/v1/tickets` | List visible tickets with `page`, `page_size`, `ticket_status` and `priority` filters |
| GET | `/api/v1/tickets/{id}` | Get ticket, comments and audit history |
| POST | `/api/v1/tickets/{id}/comments` | Add a comment |
| PATCH | `/api/v1/tickets/{id}/assignment` | Assign an agent (administrator) |
| PATCH | `/api/v1/tickets/{id}/status` | Apply a permitted lifecycle transition |

## Security notes
- Passwords are hashed using Argon2 through pwdlib.
- Access tokens are short-lived and include issuer, audience, subject, expiry and token identifier claims.
- Production startup rejects the development JWT secret. Set a unique secret of at least 32 characters using `JWT_SECRET_KEY`.
- The registration endpoint assigns the requester role. Privileged roles must never be self-assigned through public input.
- Refresh tokens expire after 30 days, are single-use, and are stored only as SHA-256 digests. Reuse of a rotated token revokes its entire session family; logout revokes the family.
- Login rate limiting defaults to five failed attempts per email and thirty per IP in fifteen minutes.
- Database schema changes are managed through Alembic. Apply migrations with `alembic upgrade head`; local Docker Compose runs this before starting the API.

## Technology
Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, PostgreSQL, pwdlib/Argon2, PyJWT, Docker, Pytest and GitHub Actions.

## Run locally
Requirements: Docker Engine with the Compose plugin.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000/docs for interactive API documentation.
Check liveness at http://localhost:8000/api/v1/health/live.
Check database readiness at http://localhost:8000/api/v1/health/ready.

Local database credentials and the example JWT secret are for development only. Never reuse them in production.

## Run tests
```bash
python -m pip install -e ".[dev]"
ruff check .
pytest --cov=service_desk_api --cov-report=term-missing
```

## Engineering principles
- Enforce permissions server-side.
- Keep business rules out of route handlers.
- Never store plaintext passwords or expose secrets in logs.
- Version database changes through migrations.
- Test success paths, invalid input, permissions and dependency failures.
- CI validates Alembic migrations and runs the application integration suite against PostgreSQL 16 using a dedicated test database. SQLite remains available as a lightweight local test option.
- Report only verified test and deployment results.

## License
MIT
