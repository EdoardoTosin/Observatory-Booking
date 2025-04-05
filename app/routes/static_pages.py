"""Module for rendering static pages.

This module provides helper functions to render static pages and sets up the corresponding
routes for the application.
"""

from flask import render_template

from .blueprint import bp


def render_static_page(template_name):
    """Helper function to render a static page template.

    Args:
        template_name (str): The name of the template file to render.

    Returns:
        Any: The rendered template.
    """
    return render_template(template_name)


@bp.route("/contact")
def contact():
    """Render the contact page.

    Returns:
        Any: The rendered 'contact.html' template.
    """
    return render_static_page("static_pages/contact.html")


@bp.route("/faq")
def faq():
    """Render the FAQ page.

    Returns:
        Any: The rendered 'faq.html' template.
    """
    return render_static_page("static_pages/faq.html")


@bp.route("/terms_of_service")
def terms_of_service():
    """Render the terms of service page.

    Returns:
        Any: The rendered 'terms_of_service.html' template.
    """
    return render_static_page("static_pages/terms_of_service.html")


@bp.route("/privacy_policy")
def privacy_policy():
    """Render the privacy policy page.

    Returns:
        Any: The rendered 'privacy_policy.html' template.
    """
    return render_static_page("static_pages/privacy_policy.html")


@bp.route("/cookie_policy")
def cookie_policy():
    """Render the cookie policy page.

    Returns:
        Any: The rendered 'cookie_policy.html' template.
    """
    return render_static_page("static_pages/cookie_policy.html")
