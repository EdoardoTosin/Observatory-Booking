"""Admin User Accounts tab regression tests: pagination/filtering, bulk
actions (both "selected" and "select all matching" scope), and the
protections around the acting admin / superadmin accounts.

Every test that needs both a set of plain users AND an admin session must
register the plain users FIRST (while logged out), since `/register` and
`/login` both redirect away immediately if the client is already
authenticated (`redirect_if_logged_in`) - registering while still logged in
as admin would silently no-op instead of creating the account.
"""

import json

from helpers import api_post, current_csrf_token, login, login_as_admin, register


def _register_n_users(client, count, prefix="bulkuser"):
    """Register `count` plain-user accounts, logging out after each so the
    client ends up logged out and ready for the caller to log in as admin."""
    for i in range(count):
        register(client, f"{prefix}{i}", f"{prefix}{i}@example.com", "Passw0rd1")
        client.get("/logout")


def test_admin_users_pagination(client):
    _register_n_users(client, 12)
    login_as_admin(client)

    response = client.get("/api/v1/admin/users?per_page=10&page=1")
    body = json.loads(response.data)
    assert body["meta"]["per_page"] == 10
    assert len(body["data"]) == 10
    assert body["meta"]["total"] == 12

    response_p2 = client.get("/api/v1/admin/users?per_page=10&page=2")
    body_p2 = json.loads(response_p2.data)
    assert len(body_p2["data"]) == 2
    # No overlap between page 1 and page 2.
    ids_p1 = {row["id"] for row in body["data"]}
    ids_p2 = {row["id"] for row in body_p2["data"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_admin_users_role_filter(client):
    _register_n_users(client, 3)
    login_as_admin(client)

    response = client.get("/api/v1/admin/users?role=Admin")
    body = json.loads(response.data)
    # No promotions have happened - only "User" role accounts exist besides
    # the superadmin (which get_paginated_users always excludes).
    assert body["data"] == []


def test_bulk_action_selected_scope(client, app):
    from app.models import User  # pylint: disable=import-outside-toplevel

    _register_n_users(client, 3)
    login_as_admin(client)

    with app.system as db:
        target_ids = [
            row.id for row in db.query(User).filter(User.role == "User").all()
        ]

    csrf = current_csrf_token(client)
    response = api_post(
        client,
        "/api/v1/admin/users/bulk",
        csrf,
        {"action": "block", "scope": "selected", "user_ids": target_ids},
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["succeeded"] == len(target_ids)

    with app.system as db:
        blocked_count = db.query(User).filter(User.blocked.is_(True)).count()
        assert blocked_count == len(target_ids)


def test_bulk_action_all_matching_scope(client, app):
    from app.models import User  # pylint: disable=import-outside-toplevel

    _register_n_users(client, 5)
    login_as_admin(client)

    csrf = current_csrf_token(client)
    response = api_post(
        client,
        "/api/v1/admin/users/bulk",
        csrf,
        {"action": "block", "scope": "all_matching", "filters": {"status": "active"}},
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["succeeded"] == 5

    with app.system as db:
        active_count = db.query(User).filter(User.blocked.is_(False)).count()
        # Only the acting superadmin should remain unblocked.
        assert active_count == 1


def test_bulk_action_protects_acting_admin_and_superadmin(client, app):
    from app.models import User  # pylint: disable=import-outside-toplevel

    _register_n_users(client, 2)
    login_as_admin(client)

    with app.system as db:
        superadmin = db.query(User).filter(User.admin_rank == "super").first()
        all_ids = [row.id for row in db.query(User).all()]

    csrf = current_csrf_token(client)
    response = api_post(
        client,
        "/api/v1/admin/users/bulk",
        csrf,
        {"action": "block", "scope": "selected", "user_ids": all_ids},
    )
    body = json.loads(response.data)
    # The superadmin (the acting admin here) must be excluded from the count.
    assert body["data"]["skipped"] >= 1

    with app.system as db:
        refreshed_superadmin = db.query(User).filter(User.id == superadmin.id).first()
        assert refreshed_superadmin.blocked is False


def test_non_superadmin_cannot_delete_users(client, app):
    """
    IDOR/privilege-escalation regression: a plain Admin (not the bootstrapped
    superadmin) must not be able to delete user accounts via the delete route.
    """
    from app.models import User  # pylint: disable=import-outside-toplevel

    register(client, "Promotable", "promotable@example.com", "Passw0rd1")
    client.get("/logout")

    login_as_admin(client)
    with app.system as db:
        target = db.query(User).filter(User.name == "Promotable").first()
        target_id = target.id
    role_csrf = current_csrf_token(client)
    client.post(
        "/admin/user/role",
        data={
            "user_id": str(target_id),
            "new_role": "Admin",
            "_csrf_token": role_csrf,
        },
        follow_redirects=True,
    )
    client.get("/logout")

    login(client, "promotable@example.com", "Passw0rd1")
    csrf = current_csrf_token(client)
    response = client.post(
        "/admin/user/delete",
        data={"user_id": str(target_id), "_csrf_token": csrf},
        follow_redirects=True,
    )
    assert b"Only superadmin can delete user accounts" in response.data
