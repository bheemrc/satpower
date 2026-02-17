"""Sphinx configuration for satpower documentation."""

project = "satpower"
copyright = "2026, satpower contributors"
author = "satpower contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "alabaster"
html_static_path = ["_static"]
