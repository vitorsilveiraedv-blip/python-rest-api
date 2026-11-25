# Architecture

## Overview

The Service Desk API is a modular monolith built with FastAPI, SQLAlchemy 2, Pydantic Settings and PostgreSQL. HTTP endpoints are kept separate from application services and persistence models. The API is versioned under `/api/v1`.

## Main boundaries

- **HTTP delivery:** route modules validate requests, call application services and translate known application errors into HTTP responses.
- **Application services:** authentication and ticket workflows enforce business rules independently of HTTP response formatting.
- **Persistence:** SQLAlchemy models and Alembic migrations define the durable data model.
- **Configuration and security:** environment-driven settings, Argon2 password hashes and signed JWT access tokens.

## Authentication

Registration creates requester accounts only. Login uses generic credential errors and performs a dummy Argon2 verification for unknown email addresses to reduce timing-based account enumeration. Access tokens are short-lived and include issuer, audience, subject, token type and token identifier claims. Current-user authorization checks the active user record, so deactivation invalidates already-issued access tokens.

Failed login attempts are limited using PostgreSQL-backed counters. The system tracks separate HMAC digests for normalized email addresses and client IP addresses, never storing those raw identifiers in the rate-limit table. The default policy allows five failed attempts per email and thirty per IP in a fifteen-minute window. The API returns HTTP 429 and a `Retry-After` header after a budget is exhausted. Successful authentication clears the email counter. Counters older than one day are cleaned during failed-login writes.

The API uses `request.client.host` as the client IP. Deployments behind a reverse proxy must configure trusted proxy handling at the ASGI server or ingress layer; the application must not blindly trust arbitrary forwarded headers.

Login rate limiting is a first layer of abuse protection, not a replacement for edge-level controls, monitoring, alerting or credential-stuffing detection. Refresh tokens are cryptographically random opaque values. Only SHA-256 hashes are persisted. Each token belongs to a session family and is single-use: a successful refresh revokes the presented token and creates a replacement. Reuse of a previously rotated token revokes the entire family. Logout also revokes the complete family. Refresh attempts check that the user remains active.

The current access token is not stored in the session table and remains valid until its short expiry after logout. Account deactivation is checked on each authenticated request and invalidates access immediately. The session family is locked during rotation to prevent two concurrent refreshes from both succeeding on PostgreSQL.

## Ticket workflow

Requesters can create and view their own tickets. Agents can view tickets assigned to them or currently unassigned. Administrators can view all tickets and assign work to active agents or administrators. Ticket state transitions are validated in the application service, and creation, comments, assignment and status changes produce audit events.

## Delivery status

- [x] Application factory and versioned routes
- [x] Environment-based settings and production JWT secret validation
- [x] PostgreSQL persistence and Alembic migrations
- [x] Argon2 password hashing and JWT authentication
- [x] Active-account checks and login rate limiting
- [x] Ticket lifecycle, visibility, assignment and audit events
- [x] PostgreSQL-backed CI integration tests
- [x] Refresh-token rotation, reuse detection and session-family revocation
- [ ] Operational metrics, alerting and production deployment hardening
