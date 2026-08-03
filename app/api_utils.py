"""Shared helpers for the /api/v1 JSON API.

Keeps every endpoint's response shaped as the same `{data, meta, errors}`
envelope (see the API routes in user_actions.py/admin_dashboard.py) instead
of each one hand-rolling its own `jsonify(...)` error tail.
"""

from flask import jsonify


def api_error(message: str, status: int = 500):
    """Build a JSON error response using the standard `{data, errors}` envelope.

    Args:
        message (str): Human-readable error message.
        status (int): HTTP status code to respond with.

    Returns:
        Tuple[Response, int]: A Flask response/status pair.
    """
    return jsonify(data=None, errors=[{"message": message}]), status
