"""
This module ensures all route modules are imported and linked
to the central Flask blueprint declared in blueprint.py.
"""

from . import (
    core_views,
    authentication,
    user_actions,
    admin_dashboard,
    error_handlers,
    static_pages,
)
