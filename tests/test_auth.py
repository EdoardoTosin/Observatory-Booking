"""Registration, login, and session/CSRF regression tests."""

from helpers import current_csrf_token, get_csrf_token, login, login_as_admin, register


def test_register_creates_account_and_logs_in(client):
    response = register(client, "Test User", "testuser@example.com", "Passw0rd1")
    assert response.status_code == 200
    assert b"Registration successful" in response.data


def test_register_rejects_weak_password(client):
    response = register(client, "Weak Pw", "weakpw@example.com", "weak")
    assert response.status_code == 200
    assert b"Password must be at least 8 characters" in response.data


def test_register_rejects_duplicate_email(client):
    register(client, "First User", "dupe@example.com", "Passw0rd1")
    client.get("/logout")
    response = register(client, "Second User", "dupe@example.com", "Passw0rd2")
    assert b"Email already registered" in response.data


def test_login_success(client):
    register(client, "Login User", "loginuser@example.com", "Passw0rd1")
    client.get("/logout")
    response = login(client, "loginuser@example.com", "Passw0rd1")
    assert response.status_code == 200
    assert b"Events" in response.data


def test_login_wrong_password(client):
    register(client, "Wrong Pw", "wrongpw@example.com", "Passw0rd1")
    client.get("/logout")
    response = login(client, "wrongpw@example.com", "NotThePassword1")
    assert b"Invalid credentials" in response.data


def test_login_blocked_account_is_rejected(client, app):
    register(client, "Blocked User", "blockeduser@example.com", "Passw0rd1")
    with app.system as db:
        from app.models import User  # pylint: disable=import-outside-toplevel

        user = db.query(User).filter(User.name == "Blocked User").first()
        user_id = user.id
    client.get("/logout")

    # AdminService.block_user reads Flask's request-bound `session` proxy
    # internally, so it must be exercised through a real request (the admin
    # route) rather than called directly outside any request context.
    login_as_admin(client)
    csrf = current_csrf_token(client)
    client.post(
        "/admin/user/block",
        data={"user_id": str(user_id), "block": "true", "_csrf_token": csrf},
        follow_redirects=True,
    )
    client.get("/logout")

    response = login(client, "blockeduser@example.com", "Passw0rd1")
    assert b"Your account is blocked" in response.data


def test_logout_clears_session(client):
    register(client, "Logout User", "logoutuser@example.com", "Passw0rd1")
    client.get("/logout")
    response = client.get("/events", follow_redirects=True)
    assert b"Login" in response.data or response.request.path == "/login"


def test_admin_login_works(client):
    response = login_as_admin(client)
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data


def test_post_without_csrf_token_is_rejected(client):
    # No CSRF token in the payload at all - the before_request hook must
    # short-circuit with a 403, not silently process the login.
    response = client.post(
        "/login", data={"email": "admin@example.com", "password": "admin"}
    )
    assert response.status_code == 403


def test_post_with_wrong_csrf_token_is_rejected(client):
    get_csrf_token(client, "/login")  # establishes a session CSRF token
    response = client.post(
        "/login",
        data={
            "email": "admin@example.com",
            "password": "admin",
            "_csrf_token": "not-the-real-token",
        },
    )
    assert response.status_code == 403
