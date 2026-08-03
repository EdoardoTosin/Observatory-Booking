"""Session helpers shared between route decorators and template rendering.

Kept separate from utils.py (a generic, low-level module: encryption, rate
limiting, env vars) since this needs the `User` model directly - importing
it from utils.py would create a models<->utils import cycle.
"""

from flask import g, session, current_app

from .models import User

_LIVE_USER_UNSET = object()


def get_live_session_user():
    """
    Fetch the current session user's live database record, cached in
    Flask's request-scoped `g` for the duration of the request.

    Both the login/admin_required decorators and the template context
    processor need to re-verify blocked/role status against the database
    on every request (the session snapshot is only refreshed at login).
    Caching the lookup in `g` means that verification happens at most once
    per request no matter how many callers need it, instead of once per
    caller.

    Returns:
        Optional[User]: The current `User` row, or None if not logged in or
            the account no longer exists.
    """
    cached = g.get("live_session_user_cache", _LIVE_USER_UNSET)
    if cached is not _LIVE_USER_UNSET:
        return cached

    user_session = session.get("user")
    if not user_session:
        g.live_session_user_cache = None
        return None

    db_session = current_app.system.session_local()  # type: ignore[attr-defined]
    try:
        user = db_session.query(User).filter_by(id=user_session.get("id")).first()
    finally:
        db_session.close()

    g.live_session_user_cache = user
    return user
