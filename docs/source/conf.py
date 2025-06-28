# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../..')) # Points to the project root
sys.path.insert(0, os.path.abspath('../../src')) # Points directly to src

project = 'CodeDocs'
copyright = '2025, Jules AI'
author = 'Jules AI'

version = '0.1'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon', # For Google and NumPy style docstrings
    'sphinx.ext.viewcode', # To add links to source code
    'sphinx.ext.autosummary', # To generate summary tables
    'sphinx_rtd_theme', # Read the Docs theme
]

autosummary_generate = True # Enable autosummary

templates_path = ['_templates']
exclude_patterns = []

language = 'en'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme' # Use Read the Docs theme
html_static_path = ['_static']
