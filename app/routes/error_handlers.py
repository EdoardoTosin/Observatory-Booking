"""
This module handles error responses and renders custom error pages for the application.
"""

from flask import render_template

from .blueprint import bp


@bp.app_errorhandler(404)
def page_not_found(_e):
    """Renders the 404 error page.

    Args:
        _e (Exception): The exception that triggered the 404 error.

    Returns:
        Tuple[Any, int]: The rendered 404 template and the HTTP status code.
    """
    return render_template("error_pages/404.html"), 404


@bp.app_errorhandler(403)
def forbidden(_e):
    """Renders the 403 error page.

    Args:
        _e (Exception): The exception that triggered the 403 error.

    Returns:
        Tuple[Any, int]: The rendered 403 template and the HTTP status code.
    """
    return render_template("error_pages/403.html"), 403


@bp.app_errorhandler(500)
def internal_error(_e):
    """Renders the 500 error page.

    Args:
        _e (Exception): The exception that triggered the 500 error.

    Returns:
        Tuple[Any, int]: The rendered 500 template and the HTTP status code.
    """
    return render_template("error_pages/500.html"), 500
