import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# Project info
project = "Observatory Booking"
copyright = "2025, Edoardo Tosin"
author = "Edoardo Tosin"

# Extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinxcontrib.httpdomain",
    "sphinx_copybutton",
    "sphinxcontrib.openapi",
]

# GitHub documentation path
html_context = {
    "github_user": "EdoardoTosin",
    "github_repo": "Observatory-Booking",
    "github_version": "main",
    "doc_path": "docs",
}

# Autodoc options
autodoc_default_options = {
    "show-inheritance": True,
    "members": True,
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# httpdomain settings
http_strict_mode = True
http_index_localname = "HTTP Routing Table"
http_index_shortname = 'api'

# Theme settings
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "logo": {
        "text": "Observatory Booking",
        "image_light": "logo.png",
        "image_dark": "logo.png",
    },
    "navbar_start": ["navbar-logo"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "show_nav_level": 3,
    "use_edit_page_button": False,
    "collapse_navigation": True,
    "navigation_depth": 4,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/EdoardoTosin/Observatory-Booking",
            "icon": "fa-brands fa-github",
        },
    ],
}

# Add static files
html_static_path = ["_static"]
html_favicon = "_static/favicon.ico"
html_css_files = ["css/custom.css"]

# Other settings
autodoc_member_order = "bysource"
autoclass_content = "both"
add_module_names = False

# Exclude folder and files
exclude_patterns = ["observatory_booking.db", "Thumbs.db", ".DS_Store"]
