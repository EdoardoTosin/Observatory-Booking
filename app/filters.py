"""Template filters and context processors module.

This module provides a context processor to inject global variables into all Flask templates.
It supports dynamic inclusion of environment-specific metadata and session-based user data.
"""

from datetime import datetime, timezone
from flask import session, current_app, flash, request, url_for

from .session_utils import get_live_session_user


def preserve_query(endpoint, **overrides):
    """
    Build a URL for `endpoint` reusing the current request's query
    parameters, with `overrides` applied on top (a key set to None or ""
    is dropped). Used for pagination/filter/sort links that need to keep
    every other active filter intact - e.g. changing `page` without
    resetting `role`/`status` on the admin users list.

    Args:
        endpoint (str): The Flask endpoint name (as passed to `url_for`).
        **overrides: Query parameters to add, replace, or remove.

    Returns:
        str: The resulting URL.
    """
    params = request.args.to_dict()
    params.update(overrides)
    params = {key: value for key, value in params.items() if value not in (None, "")}
    return url_for(endpoint, **params)  # type: ignore[arg-type]


def inject_globals():
    """
    Inject global variables into all Flask templates for consistent and contextual rendering.

    Injected Variables:
        - current_year (int): Current year in UTC.
        - current_user (dict | None): Basic user info from session if authenticated, or None.
        - is_superadmin (bool): True if user has superadmin privileges.
        - is_admin (bool): True if user is an admin.
        - flask_env (str, optional): Flask environment (only in development mode).
        - debug (bool, optional): Flask debug status (only in development mode).

    Behavior:
        - Validates that session user exists in DB; clears session if user has been deleted.
        - Adds debug info only when app is in development mode.
        - Reuses the same per-request cached lookup as login_required/admin_required
          (see get_live_session_user) instead of re-querying the database.

    Returns:
        dict: A dictionary of variables globally accessible in templates.
    """
    try:
        user_session = session.get("user", None)

        current_user = None
        is_superadmin = False
        is_admin = False

        if user_session:
            db_user = get_live_session_user()
            if db_user:
                current_user = {
                    "id": user_session.get("id"),
                    "name": user_session.get("name"),
                    "email": user_session.get("email"),
                    "role": user_session.get("role"),
                }
                is_superadmin = user_session.get("admin_rank") == "super"
                is_admin = user_session.get("role") == "Admin"
            else:
                session.clear()
                flash("Your account has been deleted.", "error")

        is_dev = current_app.config.get("ENV", "production") == "development"

        debug_info = (
            {
                "flask_env": current_app.config.get("ENV"),
                "debug": current_app.debug,
            }
            if is_dev
            else {}
        )

        return {
            "current_year": datetime.now(timezone.utc).year,
            "current_user": current_user,
            "is_superadmin": is_superadmin,
            "is_admin": is_admin,
            **debug_info,
        }

    except (KeyError, AttributeError, RuntimeError) as e:
        current_app.logger.warning("Failed to extract session or config data: %s", e)
        return {
            "current_year": datetime.now(timezone.utc).year,
            "current_user": None,
            "is_superadmin": False,
            "is_admin": False,
        }


def init_filters(app):
    """
    Register context processors and template globals with the Flask app.

    Args:
        app (Flask): The Flask application instance.
    """
    app.context_processor(inject_globals)
    app.add_template_global(preserve_query, name="preserve_query")
