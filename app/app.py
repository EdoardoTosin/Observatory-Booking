"""Flask booking system application module.

This module serves as the main logic for the Flask booking system. It handles:

- Creation and configuration of the Flask app instance.
- Environment-based settings for development or production modes.
- Running the app using Flask's development server or Waitress for production.
"""

from flask import Flask
from waitress import serve

from .booking_system import BookingSystem
from .utils import logger, get_secret_key, get_env_value
from .filters import init_filters
from .routes.blueprint import bp


def create_instance(debug=False):
    """
    Create and configure the Flask application instance.

    Initializes the Flask app, sets secure configurations for production,
    binds core services, registers custom filters, and sets up route blueprints.

    Args:
        debug (bool): Indicates whether the app should run in debug mode.

    Returns:
        Flask: A fully configured Flask app instance ready to run.
    """
    instance = Flask(__name__)
    instance.secret_key = get_secret_key()

    if not debug:
        instance.config.update(
            WTF_CSRF_ENABLED=bool(get_env_value("WTF_CSRF_ENABLED", True)),
            SESSION_COOKIE_DOMAIN=get_env_value("SESSION_COOKIE_DOMAIN", None),
            SESSION_COOKIE_HTTPONLY=bool(
                get_env_value("SESSION_COOKIE_HTTPONLY", True)
            ),
            SESSION_COOKIE_SECURE=bool(get_env_value("SESSION_COOKIE_SECURE", True)),
            SESSION_COOKIE_SAMESITE=get_env_value("SESSION_COOKIE_SAMESITE", "Strict"),
        )

    instance.system = BookingSystem()  # type: ignore[attr-defined]

    init_filters(instance)

    instance.register_blueprint(bp)

    return instance


def run_app(app, host, port, debug_mode, **kwargs):
    """
    Run the Flask application using the appropriate server for the environment.

    Args:
        app (Flask): The configured Flask app instance.
        host (str): Host IP address or hostname.
        port (int): Port number for the server.
        debug_mode (bool): Flag to enable or disable debug mode.
        **kwargs: Additional keyword arguments for server configuration.

    Note:
        This function does not validate host or port values explicitly.
    """
    if debug_mode:
        logger.info("Running in development mode on %s:%s", host, port)
        app.run(debug=True, host=host, port=port, **kwargs)
    else:
        logger.info("Running in production mode on %s:%s", host, port)
        serve(app, host=host, port=port, **kwargs)


def main():
    """
    Main entry point for starting the Flask application.

    Retrieves environment variables for host, port, and debug mode settings.
    Initializes the app instance and starts the server using the appropriate mode.
    """
    host = get_env_value("HOST", "127.0.0.1")
    port = int(get_env_value("PORT", "5000"))
    debug_mode = get_env_value("DEBUG_MODE", "False").lower() == "true"

    app = create_instance(debug=debug_mode)

    run_app(app, host, port, debug_mode)
