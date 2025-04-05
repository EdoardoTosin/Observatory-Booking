"""Module entry point for the Observatory Booking Web App.

This file enables the Flask application to be executed using Python's module execution syntax:

    $ python -m app

When executed, it delegates control to the `main()` function defined in `app.py`,
which is responsible for initializing the Flask application instance and starting
the appropriate server based on the environment (development or production).
"""

from .app import main

if __name__ == "__main__":
    main()
