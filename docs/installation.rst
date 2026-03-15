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

Running the Application
-----------------------

Start the Flask app:

.. code-block:: bash

    uv run python -m app

The Superadmin account is created automatically on first run. Credentials are printed once to stdout and are never written to log files.

Access the application at `http://127.0.0.1:5000/`.

For production, use Waitress behind a reverse proxy (e.g., Nginx, Apache).
