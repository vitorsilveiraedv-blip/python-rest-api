# Service Desk API

A Python REST API for IT service desk operations, developed as a modular monolith with clear boundaries between HTTP delivery, application logic, domain rules and persistence.

> **Project status:** foundation milestone. Application configuration, versioned routing, health checks, Docker-based local infrastructure and CI are in place. Authentication, ticket workflows and audit features are planned, not yet implemented.

## Current foundation
- FastAPI application factory and versioned API routing.
- Environment-driven settings with Pydantic Settings.
- SQLAlchemy 2 engine and request-scoped database sessions.
- Liveness endpoint independent of external services.
- Readiness endpoint that verifies database connectivity.
- Dockerfile and Docker Compose configuration for local PostgreSQL.
- Pytest suite and Ruff linting in GitHub Actions.

## Planned capabilities
- Secure authentication and role-based authorization.
- Requester, agent and administrator roles.
- Ticket intake, assignment, priorities and validated status transitions.
- Comments and append-only audit history.
- Search, filtering, sorting, pagination and operational metrics.

See [Architecture and Technical Specification](docs/architecture.md) for design, domain model, security principles and acceptance criteria.

## Technology
Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, PostgreSQL, Docker, Pytest and GitHub Actions.

## Run locally
Requirements: Docker Engine with the Compose plugin.

```bash
docker compose up --build
```

Open http://localhost:8000/docs for interactive API documentation.
Check liveness at http://localhost:8000/api/v1/health/live.
Check database readiness at http://localhost:8000/api/v1/health/ready.

Local database credentials are for development only. Never reuse them in production.

## Run tests
```bash
python -m pip install -e ".[dev]"
ruff check .
pytest --cov=service_desk_api --cov-report=term-missing
```

Copy `.env.example` to `.env` and adjust values for local development. Never commit real credentials.

## Engineering principles
- Enforce permissions server-side.
- Keep business rules out of route handlers.
- Never store plaintext passwords or expose secrets in logs.
- Version database changes through migrations.
- Test success paths, invalid input, permissions and dependency failures.
- Report only verified test and deployment results.

## License
MIT