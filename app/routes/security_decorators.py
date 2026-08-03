"""Module containing security decorators and CSRF helpers for route access control.

This module provides decorators to enforce login and admin access for Flask routes,
and utility functions for session-based CSRF token generation and validation.
"""

import hmac
import secrets
from functools import wraps
from flask import session, flash, redirect, url_for, request, abort

from ..api_utils import api_error
from ..session_utils import get_live_session_user

_CSRF_TOKEN_KEY = "_csrf_token"
_CSRF_FIELD_NAME = "_csrf_token"
_CSRF_HEADER_NAME = "X-CSRF-Token"

_API_PATH_PREFIX = "/api/"


def _is_api_request() -> bool:
    """Return True if the current request targets the JSON API namespace."""
    return request.path.startswith(_API_PATH_PREFIX)


def _unauthorized_response(message: str, api_status: int):
    """Return a JSON error for `/api/` requests, or a flash + login redirect."""
    if _is_api_request():
        return api_error(message, api_status)
    flash(message, "error")
    return redirect(url_for("bp.login"))


def generate_csrf_token() -> str:
    """Return the current session CSRF token, creating one if absent.

    Returns:
        str: A hex-encoded 32-byte random token stored in the session.
    """
    if _CSRF_TOKEN_KEY not in session:
        session[_CSRF_TOKEN_KEY] = secrets.token_hex(32)
    return str(session[_CSRF_TOKEN_KEY])


def validate_csrf():
    """Validate the CSRF token for state-changing requests (POST/PUT/DELETE/PATCH).

    Reads the submitted token from the `X-CSRF-Token` header for JSON requests
    (the `/api/` namespace) and from the `_csrf_token` form field otherwise.
    GET, HEAD, and OPTIONS requests are exempt.

    Returns:
        Optional[Response]: A JSON error response for a failed `/api/` request
            (the caller must return this to short-circuit the request), or
            None if the request is valid/exempt. Aborts with HTTP 403 directly
            for non-API requests.
    """
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return None

    session_token = session.get(_CSRF_TOKEN_KEY)
    submitted_token = (
        request.headers.get(_CSRF_HEADER_NAME)
        if request.is_json
        else request.form.get(_CSRF_FIELD_NAME)
    )
    is_valid = bool(
        session_token
        and submitted_token
        and hmac.compare_digest(session_token, submitted_token)
    )
    if is_valid:
        return None
    if _is_api_request():
        return api_error("Invalid or missing CSRF token.", 403)
    abort(403)
    return None  # unreachable; abort() always raises


def login_required(f):
    """Decorator to ensure that a user is logged in before accessing a route.

    Re-validates the account's existence and blocked status against the
    database on every request, since the Flask session is only refreshed at
    login and would otherwise keep granting access after an admin blocks the
    account or deletes it. `/api/` routes get a JSON 401 instead of a
    redirect, since a `fetch()` caller can't act on a login-page redirect.

    Args:
        f (Callable[..., Any]): The route function to be decorated.

    Returns:
        Callable[..., Any]: The decorated function that enforces login.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            return _unauthorized_response(
                "You must be logged in to access this page.", 401
            )

        db_user = get_live_session_user()
        if not db_user:
            session.clear()
            return _unauthorized_response("Your account no longer exists.", 401)
        if db_user.blocked:
            session.clear()
            return _unauthorized_response("Your account has been blocked.", 403)
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to ensure that the current user has admin privileges.

    Re-validates the account's role and blocked status against the database
    on every request, since the Flask session is only refreshed at login and
    would otherwise keep granting admin access after an admin is demoted,
    blocked, or deleted. `/api/` routes get a JSON 403 instead of a redirect,
    since a `fetch()` caller can't act on a login-page redirect.

    Args:
        f (Callable[..., Any]): The route function to be decorated.

    Returns:
        Callable[..., Any]: The decorated function that enforces admin access.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            return _unauthorized_response(
                "Access denied. Admin privileges required.", 401
            )

        db_user = get_live_session_user()
        if not db_user or db_user.blocked or db_user.role != "Admin":
            session.clear()
            return _unauthorized_response(
                "Access denied. Admin privileges required.", 403
            )
        return f(*args, **kwargs)

    return decorated_function
