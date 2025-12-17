project = "CausaGanha"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "alabaster"

# Make package importable
import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

