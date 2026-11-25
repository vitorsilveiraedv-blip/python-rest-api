# Service Desk API

A Python REST API for IT service desk operations, developed as a modular monolith with clear boundaries between HTTP delivery, application logic, domain rules and persistence.

> **Project status:** authentication milestone implemented. The API supports requester registration, Argon2 password hashing, signed short-lived JWT access tokens, authenticated profile retrieval and role authorization dependencies. Ticket workflows, persistent refresh-token rotation, audit events and database migrations remain planned work.

## Implemented capabilities
- FastAPI application factory and versioned API routing.
- Environment-driven settings with Pydantic Settings.
- SQLAlchemy 2 persistence models and request-scoped database sessions.
- Liveness and database-readiness health endpoints.
- Requester registration with normalized unique email addresses.
- Argon2 password hashing; plaintext passwords are never stored.
- JWT access tokens validated for signature, issuer, audience, expiry and token type.
- Authenticated `/auth/me` endpoint and reusable role-based authorization dependency.
- Generic authentication errors that do not reveal whether an account exists.
- Dockerfile and Docker Compose configuration for local PostgreSQL.
- Pytest integration tests and Ruff linting in GitHub Actions.

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health/live` | Process liveness |
| GET | `/api/v1/health/ready` | Database readiness |
| POST | `/api/v1/auth/register` | Register a requester |
| POST | `/api/v1/auth/login` | Obtain an access token |
| GET | `/api/v1/auth/me` | Retrieve the authenticated profile |

## Security notes
- Passwords are hashed using Argon2 through pwdlib.
- Access tokens are short-lived and include issuer, audience, subject, expiry and token identifier claims.
- Production startup rejects the development JWT secret. Set a unique secret of at least 32 characters using `JWT_SECRET_KEY`.
- The registration endpoint assigns the requester role. Privileged roles must never be self-assigned through public input.
- Access tokens are currently stateless and there is no refresh-token or revocation endpoint yet.
- Versioned Alembic migrations are a next milestone.

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
- Report only verified test and deployment results.

## License
MIT
