# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'PyKE'
copyright = '2007-2021, Bruce Frederiksen'
author = 'Bruce Frederiksen'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'links.rst']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinxdoc'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Custom behaviour


def fix_ref(ref, html_dir):
    """Fixes a reference prepending it with a relative path (if necessary)
    """
    # Is it either another link or an external page?
    if ref.rstrip()[-1] == '_' or ref.startswith('http://'):
        return ref
    else:
        return os.path.join(html_dir, ref)


source_dir = os.path.dirname(os.path.relpath(__file__, 'pyke/doc/sphinx/'))
html_dir = os.path.join(source_dir, '../build/html')

# Example from https://stackoverflow.com/a/61694897
rst_epilog = ""
with open('links.rst') as f:
    for line in f:
        link, ref = line.split(':', 1)
        rst_epilog += link + ": " + fix_ref(ref, html_dir)
