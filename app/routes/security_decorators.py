"""Module containing security decorators and CSRF helpers for route access control.

This module provides decorators to enforce login and admin access for Flask routes,
and utility functions for session-based CSRF token generation and validation.
"""

import hmac
import secrets
from functools import wraps
from flask import session, flash, redirect, url_for, request, abort

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


def login_required(f):
    """Decorator to ensure that a user is logged in before accessing a route.

    If the user is not logged in, flashes an error message and redirects to the login page.

    Args:
        f (Callable[..., Any]): The route function to be decorated.

    Returns:
        Callable[..., Any]: The decorated function that enforces login.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for("bp.login"))
        if user.get("blocked", False):
            flash("Your account has been blocked.", "error")
            return redirect(url_for("bp.login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to ensure that the current user has admin privileges.

    If the user is not an admin, flashes an error message and redirects to the login page.

    Args:
        f (Callable[..., Any]): The route function to be decorated.

    Returns:
        Callable[..., Any]: The decorated function that enforces admin access.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user", {}).get("role") != "Admin":
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("bp.login"))
        return f(*args, **kwargs)

    return decorated_function
