"""Template filters and context processors module.

This module provides a context processor to inject global variables into all Flask templates.
It supports dynamic inclusion of environment-specific metadata and session-based user data.
"""

from datetime import datetime, timezone
from flask import session, current_app, flash

from .models import User


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
        - Ensures DB session is properly closed after query.

    Returns:
        dict: A dictionary of variables globally accessible in templates.
    """
    try:
        user_session = session.get("user", None)

        current_user = None
        is_superadmin = False
        is_admin = False

        if user_session:
            db_session = current_app.system.session_local()  # type: ignore[attr-defined]
            try:
                db_user = (
                    db_session.query(User).filter_by(id=user_session["id"]).first()
                )
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
            finally:
                db_session.close()

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
    Register context processors (and filters, if any) with the Flask app.

    Args:
        app (Flask): The Flask application instance.
    """
    app.context_processor(inject_globals)
