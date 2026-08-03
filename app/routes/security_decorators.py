"""Module containing security decorators and CSRF helpers for route access control.

This module provides decorators to enforce login and admin access for Flask routes,
and utility functions for session-based CSRF token generation and validation.
"""

import hmac
import secrets
from functools import wraps
from flask import session, flash, redirect, url_for, request, abort, current_app

from ..models import User

_CSRF_TOKEN_KEY = "_csrf_token"
_CSRF_FIELD_NAME = "_csrf_token"


def generate_csrf_token() -> str:
    """Return the current session CSRF token, creating one if absent.

    Returns:
        str: A hex-encoded 32-byte random token stored in the session.
    """
    if _CSRF_TOKEN_KEY not in session:
        session[_CSRF_TOKEN_KEY] = secrets.token_hex(32)
    return str(session[_CSRF_TOKEN_KEY])


def validate_csrf() -> None:
    """Validate the CSRF token for state-changing requests (POST/PUT/DELETE/PATCH).

    Aborts with HTTP 403 if the submitted token does not match the session token.
    GET, HEAD, and OPTIONS requests are exempt.
    """
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return
    session_token = session.get(_CSRF_TOKEN_KEY)
    submitted_token = request.form.get(_CSRF_FIELD_NAME)
    if not session_token or not submitted_token:
        abort(403)
    if not hmac.compare_digest(session_token, submitted_token):
        abort(403)


def _get_live_user():
    """Fetch the current session user's live record from the database.

    Re-checking the database on every request (rather than trusting the
    session snapshot taken at login) ensures that a block or role change
    applied by an admin takes effect immediately, instead of only after the
    affected user's session expires or they log out.

    Returns:
        Optional[User]: The current `User` row, or None if not logged in or
            the account no longer exists.
    """
    user_session = session.get("user")
    if not user_session:
        return None
    db_session = current_app.system.session_local()  # type: ignore[attr-defined]
    try:
        return db_session.query(User).filter_by(id=user_session.get("id")).first()
    finally:
        db_session.close()


def login_required(f):
    """Decorator to ensure that a user is logged in before accessing a route.

    Re-validates the account's existence and blocked status against the
    database on every request, since the Flask session is only refreshed at
    login and would otherwise keep granting access after an admin blocks the
    account or deletes it.

    Args:
        f (Callable[..., Any]): The route function to be decorated.

    Returns:
        Callable[..., Any]: The decorated function that enforces login.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for("bp.login"))

        db_user = _get_live_user()
        if not db_user:
            session.clear()
            flash("Your account no longer exists.", "error")
            return redirect(url_for("bp.login"))
        if db_user.blocked:
            session.clear()
            flash("Your account has been blocked.", "error")
            return redirect(url_for("bp.login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to ensure that the current user has admin privileges.

    Re-validates the account's role and blocked status against the database
    on every request, since the Flask session is only refreshed at login and
    would otherwise keep granting admin access after an admin is demoted,
    blocked, or deleted.

    Args:
        f (Callable[..., Any]): The route function to be decorated.

    Returns:
        Callable[..., Any]: The decorated function that enforces admin access.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("bp.login"))

        db_user = _get_live_user()
        if not db_user or db_user.blocked or db_user.role != "Admin":
            session.clear()
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("bp.login"))
        return f(*args, **kwargs)

    return decorated_function
