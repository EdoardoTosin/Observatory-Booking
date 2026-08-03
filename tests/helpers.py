"""Shared test helper functions (not fixtures - plain imports) for driving
the Flask test client through CSRF-protected form and JSON API endpoints.
"""

import json

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin"


def get_csrf_token(client, path):
    """Fetch a page and pull the `_csrf_token` hidden field out of its HTML."""
    response = client.get(path)
    return response.text.split('name="_csrf_token" value="')[1].split('"')[0]


def register(client, name, email, password):
    """Register a new account and return the redirect response."""
    csrf = get_csrf_token(client, "/register")
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm": password,
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )


def login(client, email, password):
    """Log in and return the redirect response."""
    csrf = get_csrf_token(client, "/login")
    return client.post(
        "/login",
        data={"email": email, "password": password, "_csrf_token": csrf},
        follow_redirects=True,
    )


def login_as_admin(client):
    """Log in as the bootstrapped superadmin (admin@example.com / admin)."""
    return login(client, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD)


def api_post(client, path, csrf, payload):
    """POST JSON to an `/api/v1/...` endpoint with the CSRF header set."""
    return client.post(
        path,
        headers={"X-CSRF-Token": csrf},
        content_type="application/json",
        data=json.dumps(payload),
    )


def current_csrf_token(client):
    """Pull a fresh CSRF token from any already-authenticated page.

    Uses `/change_password` rather than `/events`, since the events page
    only renders a `_csrf_token` field inside its per-event booking/cancel
    forms - with zero events (the common state right after a DB reset) the
    page has no CSRF field at all. `/change_password`'s form is static and
    always present regardless of data state.
    """
    response = client.get("/change_password")
    return response.text.split('name="_csrf_token" value="')[1].split('"')[0]
