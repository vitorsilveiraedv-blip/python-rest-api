PASSWORD = "a-very-long-test-password"


def register_and_login(client, email: str) -> tuple[dict, dict]:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test Person", "password": PASSWORD},
    )
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return registration.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


def set_role(client, user_id: str, role) -> None:
    from uuid import UUID

    from service_desk_api.models.user import User

    with client.app.state.testing_session_factory() as session:
        user = session.get(User, UUID(user_id))
        user.role = role
        session.commit()


def create_ticket(client, headers: dict) -> dict:
    response = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "title": "Cannot access email",
            "description": "The company email account rejects my password.",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_requester_can_create_comment_and_read_audit_history(client):
    _, headers = register_and_login(client, "requester@example.com")
    ticket = create_ticket(client, headers)

    comment = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        headers=headers,
        json={"body": "I have already tried resetting my password."},
    )
    assert comment.status_code == 201

    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["comments"]) == 1
    assert [event["event_type"] for event in detail.json()["events"]] == [
        "created", "commented"
    ]


def test_requesters_cannot_view_another_users_ticket(client):
    _, first_headers = register_and_login(client, "first@example.com")
    ticket = create_ticket(client, first_headers)
    _, second_headers = register_and_login(client, "second@example.com")

    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=second_headers)
    listing = client.get("/api/v1/tickets", headers=second_headers)
    assert detail.status_code == 404
    assert listing.json()["items"] == []
    assert listing.json()["total"] == 0


def test_agent_can_progress_ticket_and_requester_can_close_resolved_ticket(client):
    _, requester_headers = register_and_login(client, "owner@example.com")
    ticket = create_ticket(client, requester_headers)
    agent, agent_headers = register_and_login(client, "agent@example.com")
    from service_desk_api.models.user import UserRole

    set_role(client, agent["id"], UserRole.AGENT)

    for next_status in ("in_progress", "waiting_for_requester", "in_progress", "resolved"):
        response = client.patch(
            f"/api/v1/tickets/{ticket['id']}/status",
            headers=agent_headers,
            json={"status": next_status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == next_status

    closed = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status",
        headers=requester_headers,
        json={"status": "closed"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


def test_requester_cannot_skip_ticket_lifecycle(client):
    _, headers = register_and_login(client, "lifecycle@example.com")
    ticket = create_ticket(client, headers)
    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status",
        headers=headers,
        json={"status": "resolved"},
    )
    assert response.status_code == 409


def test_only_administrator_can_assign_and_assignee_must_be_agent(client):
    from service_desk_api.models.user import UserRole

    _, requester_headers = register_and_login(client, "submitter@example.com")
    ticket = create_ticket(client, requester_headers)
    agent, _ = register_and_login(client, "assignee@example.com")
    set_role(client, agent["id"], UserRole.AGENT)

    denied = client.patch(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=requester_headers,
        json={"agent_id": agent["id"]},
    )
    assert denied.status_code == 403

    admin, admin_headers = register_and_login(client, "admin@example.com")
    set_role(client, admin["id"], UserRole.ADMINISTRATOR)
    assigned = client.patch(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={"agent_id": agent["id"]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_to_id"] == agent["id"]

def test_ticket_listing_supports_pagination_and_filters(client):
    _, headers = register_and_login(client, "paging@example.com")
    create_ticket(client, headers)
    second = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "title": "Printer is offline",
            "description": "The shared office printer is not responding.",
            "priority": "low",
        },
    )
    assert second.status_code == 201

    first_page = client.get("/api/v1/tickets?page=1&page_size=1", headers=headers)
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert first_page.json()["page_size"] == 1
    assert len(first_page.json()["items"]) == 1

    filtered = client.get("/api/v1/tickets?priority=low", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["priority"] == "low"


def test_ticket_listing_rejects_invalid_pagination(client):
    _, headers = register_and_login(client, "invalid-page@example.com")
    response = client.get("/api/v1/tickets?page=0&page_size=101", headers=headers)
    assert response.status_code == 422

