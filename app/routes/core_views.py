"""
This module contains core views for the application, including routes for the favicon
and the home page.
"""

import os
from flask import render_template, send_from_directory, current_app

from .blueprint import bp


@bp.route("/favicon.ico")
def favicon():
    """Serve the favicon.

    Retrieves the favicon from the static directory and serves it with the correct MIME type.

    Returns:
        Any: The Flask response object containing the favicon.
    """
    static_dir: str = os.path.join(current_app.root_path, "static")
    return send_from_directory(
        static_dir,
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@bp.route("/", endpoint="index")
def index():
    """Render the home page.

    Returns:
        Any: The rendered home page template.
    """
    return render_template("index.html")
