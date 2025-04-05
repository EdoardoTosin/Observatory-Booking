Installation Guide
==================

This guide details the installation and setup of the **Observatory Booking Web App**, a Flask-based web application for scheduling observatory events with weather-based automation.

Prerequisites
-------------

Ensure you have the following software installed:

- Python 3.9 or higher: https://www.python.org/downloads/
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

    pip install -r requirements.txt

Environment Configuration
-------------------------

Create a `.env` file in the project root with the following variables:

.. code-block:: ini

    DATABASE_URL=sqlite:///observatory_booking.db
    DEFAULT_ADMIN_EMAIL=admin@example.com
    DEFAULT_ADMIN_PASSWORD=admin
    SECRET_KEY=<secure_random_string>
    AES_SECRET_KEY=<base64_encoded_key>
    AES_IV=<base64_encoded_iv>
    FLASK_ENV=development
    DEBUG_MODE=True
    HOST=0.0.0.0
    PORT=5000
    WTF_CSRF_ENABLED=False
    SESSION_COOKIE_SECURE=False
    LOGGING_LEVEL=DEBUG

**Note:** For production, set `FLASK_ENV=production`, use strong secrets, and enable CSRF and secure cookies.

Running the Application
-----------------------

Start the Flask app:

.. code-block:: bash

    python -m app

Note: The Superadmin account is automatically created on first run using credentials from the `.env` file.

Access the application at `http://127.0.0.1:5000/`.

For production, use Waitress behind a reverse proxy (e.g., Nginx, Apache).
