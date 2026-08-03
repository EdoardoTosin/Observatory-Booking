"""Shared pytest fixtures for the Observatory Booking test suite.

Points the app at an isolated temp-file SQLite database (never the real
`observatory_booking.db`) and resets its schema before every test, so tests
can run in any order/combination without leaking state between them.
"""

import os
import tempfile

# Must run before any `app.*` import: `app.utils` calls `load_dotenv()` at
# import time, which only fills in variables NOT already present in
# `os.environ` - setting DATABASE_URL here first means the repo's real
# `.env` (which points at observatory_booking.db) never gets a chance to
# win, so tests can never accidentally touch production/sample data.
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="obs_booking_test_")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

import pytest  # noqa: E402  pylint: disable=wrong-import-position

from app import utils as app_utils  # noqa: E402  pylint: disable=wrong-import-position
from app.app import create_instance  # noqa: E402  pylint: disable=wrong-import-position
from app.models import Base  # noqa: E402  pylint: disable=wrong-import-position


@pytest.fixture(scope="session")
def app():
    """One Flask app (and one WeatherService/scheduler) for the whole test session."""
    flask_app = create_instance()
    flask_app.config.update(TESTING=True)
    yield flask_app
    flask_app.system.shutdown()  # type: ignore[attr-defined]
    try:
        os.remove(_TEST_DB_PATH)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _reset_db(app):  # pylint: disable=redefined-outer-name
    """Wipe and recreate every table before each test, restoring the superadmin.

    Also clears the process-global rate-limit store: `is_rate_limited` keys
    on the encrypted email/user id, which is unrelated to the database and
    would otherwise keep accumulating across every test in the session -
    repeatedly logging in as the same seeded admin account (the same
    ciphertext every time) across dozens of tests would eventually trip the
    limiter and fail unrelated, later tests.
    """
    system = app.system  # type: ignore[attr-defined]
    engine = system.session_local().get_bind()
    system.session_local.remove()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    system.admin_service._initialize_superadmin()  # pylint: disable=protected-access
    with app_utils._RATE_LIMIT_LOCK:  # pylint: disable=protected-access
        app_utils._rate_limit_store.clear()  # pylint: disable=protected-access
    yield
    system.session_local.remove()


@pytest.fixture
def client(app):  # pylint: disable=redefined-outer-name
    """A fresh Flask test client (own cookie jar) for each test."""
    return app.test_client()
