"""Module containing security decorators for route access control.

This module provides decorators to enforce login and admin access for Flask routes.
"""

from functools import wraps
from flask import session, flash, redirect, url_for


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
