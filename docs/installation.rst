Installation Guide
==================

This guide details the installation and setup of the **Observatory Booking Web App**, a Flask-based web application for scheduling observatory events with weather-based automation.

Prerequisites
-------------

Ensure you have the following software installed:

- Python 3.10 or higher: https://www.python.org/downloads/
- Git (to clone the repository): https://git-scm.com/
- SQLite (default) or PostgreSQL (optional for production)

Cloning the Repository
----------------------

Clone the repository:

.. code-block:: bash

    git clone https://github.com/EdoardoTosin/Observatory-Booking
    cd Observatory-Booking

Python Setup
------------------------

Install required Python packages:

.. code-block:: bash

    uv sync

Environment Configuration
-------------------------

Create a `.env` file in the project root. Cryptographic keys that are absent are generated automatically on first start and written back to `.env`.

.. code-block:: ini

    DATABASE_URL=sqlite:///observatory_booking.db
    DEFAULT_ADMIN_EMAIL=admin@example.com
    DEFAULT_ADMIN_PASSWORD=
    SECRET_KEY=<secure_random_string>
    AES_SECRET_KEY=<base64_encoded_key>
    AES_HMAC_KEY=<base64_encoded_key>
    AES_IV=<base64_encoded_iv>
    ENV=development
    DEBUG_MODE=False
    HOST=127.0.0.1
    PORT=5000
    SESSION_COOKIE_HTTPONLY=True
    SESSION_COOKIE_SECURE=False
    SESSION_COOKIE_SAMESITE=Lax
    LOGGING_LEVEL=INFO

Leave ``DEFAULT_ADMIN_PASSWORD`` empty. On first run the application generates a secure random password and prints it once to stdout -- change it immediately after logging in. For production set ``DEBUG_MODE=False``, ``SESSION_COOKIE_SECURE=True`` (requires HTTPS), and ``SESSION_COOKIE_SAMESITE=Strict``.

Configuration Reference
------------------------

Every environment variable the application reads, with its default when unset:

.. list-table::
   :header-rows: 1
   :widths: 22 48 30

   * - Setting
     - Description
     - Default
   * - ``DATABASE_URL``
     - SQLAlchemy connection URI.
     - ``sqlite:///observatory_booking.db``
   * - ``SECRET_KEY``
     - Flask session signing key.
     - auto-generated, written back to ``.env``
   * - ``AES_SECRET_KEY``
     - Base64 AES-256 key for personal data encryption (name/email).
     - auto-generated, written back to ``.env``
   * - ``AES_HMAC_KEY``
     - Base64 HMAC key used to derive the deterministic AES-GCM nonce.
     - auto-generated, written back to ``.env``
   * - ``AES_IV``
     - Base64 legacy AES-CBC IV, kept only to decrypt data written before the AES-GCM migration.
     - auto-generated, written back to ``.env``
   * - ``DEFAULT_ADMIN_EMAIL``
     - Email for the first-time bootstrapped superadmin account.
     - ``admin@example.com``
   * - ``DEFAULT_ADMIN_PASSWORD``
     - Password for the bootstrapped superadmin; leave blank.
     - auto-generated, printed once to stdout
   * - ``ENV``
     - Set to ``development`` to enable SQLAlchemy SQL echo logging and lower connection-pool sizing.
     - ``production``
   * - ``DEBUG_MODE``
     - Enables Flask's interactive debugger and auto-reload.
     - ``False``
   * - ``HOST``
     - Host address to bind the server to.
     - ``127.0.0.1``
   * - ``PORT``
     - Port to bind the server to.
     - ``5000``
   * - ``WTF_CSRF_ENABLED``
     - Enable CSRF protection on all state-changing endpoints (form field or ``X-CSRF-Token`` header for the JSON API).
     - ``True``
   * - ``SESSION_COOKIE_HTTPONLY``
     - Prevent JavaScript access to the session cookie.
     - ``True``
   * - ``SESSION_COOKIE_SECURE``
     - Require HTTPS for the session cookie; must stay ``True`` in production.
     - ``True``
   * - ``SESSION_COOKIE_SAMESITE``
     - SameSite policy for the session cookie.
     - ``Strict``
   * - ``SESSION_COOKIE_DOMAIN``
     - Domain for the session cookie; blank uses the current host.
     - unset
   * - ``LOGGING_LEVEL``
     - Log verbosity: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
     - ``INFO``

Running the Application
-----------------------

Start the Flask app:

.. code-block:: bash

    uv run python -m app

The Superadmin account is created automatically on first run. Credentials are printed once to stdout and are never written to log files.

Access the application at `http://127.0.0.1:5000/`.

For production, use Waitress behind a reverse proxy (e.g., Nginx, Apache).

Sample Data
-----------

``scripts/seed_sample_db.py`` replaces your local database with a freshly
seeded one for testing or demoing: a few memorable named accounts
(superadmin, an admin, two regular users, one blocked user) plus
thousands of bulk-generated users/events/bookings, so it behaves like a
real deployment rather than an empty database.

.. code-block:: bash

    uv run python scripts/seed_sample_db.py [n_users] [n_events] [bookings_per_event_avg]

Defaults to ~5000 users, 365 events, ~30 bookings/event on average. Login
credentials are written to ``SAMPLE_DATA_CREDENTIALS.md`` in the project
root (gitignored, never committed). This overwrites your existing
database, so only run it against a database you don't need.

Running the Test Suite
-----------------------

The automated regression suite runs against an isolated temp-file SQLite
database (never the real ``observatory_booking.db``), so it's always
safe to run:

.. code-block:: bash

    uv run pytest

It also runs automatically as part of ``pre-commit run --all-files``,
alongside ``black``, ``pylint``, and ``mypy``.
