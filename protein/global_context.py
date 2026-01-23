"""
Defining the GLOBAL context (capabilities) for a Protein interpreter.

NOTE:
    What we define as "global" is not the same as in most languages.
    It is simply a part of the first frame on the lexical stack,
    which contains necessary functions.

    This file should contain ONLY functions that require no interpreter state.

    (It is on top of the Jinja2 utilities.)
"""

import os

import keyring





from .sql import osquery
from .util import dequote, LITERAL_PREFIX



def jinja_assert(condition, message=None):
    """
    Assertions for expressions, necessary in a Jinja2 environment.

    e.g.:
        {{ assert(entry.title is not none, "Missing title") }}

    The explicit purpose of this function, is to provide the user of Protein
    with a tool with which to inspect what's happening on the host (Python).

    It is a "look-through" function, or 
    a _debugging hook_ that fishes the host-side state.

    There _could_ (and probably _should_) be an assert statement for Protein,
    such as .require.

    """
    assert condition, message
    return ""



def quote(value: str) -> str:
    """
    Mark the given string as literal by prefixing the #!literal sentinel.

    This transformation is idempotent: if the value is already quoted,
    it is returned unchanged. It is the inverse of `dequote`.
    """
    if not isinstance(value, str):
        raise TypeError("quote() expects a string")
    if value.startswith(LITERAL_PREFIX):
        return value
    return f"{LITERAL_PREFIX}{value}"

# ---------------------------------
# Markdown
# ---------------------------------

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.container import container_plugin
from mdit_py_plugins.front_matter import front_matter_plugin

def make_markdown_parser() -> MarkdownIt:
    """
    Create a MarkdownIt parser with standard plugins for Protein.
    It is configured to behave similarly to GitHub‑flavored Markdown.

    This is a factory function that creates a new parser instance.
    If you need a reusable instance, use the global `_md` instance.
    """
    md = (
        MarkdownIt("commonmark")
        .use(tasklists_plugin)
        .use(footnote_plugin)
        .enable("strikethrough")
        .use(front_matter_plugin)
        .enable("table")
    )

    OPTIONS = ['note', 'tip', 'warning', 'danger', 'info', 'error', 'example', 'quote']
    for option in OPTIONS:
        md = md.use(container_plugin, option)

    return md



def to_html(text: str, 
            allow_html: bool = False) -> str:
    """
    Convert Markdown text to HTML using markdown-it-py,
    with a GitHub‑like flavor.

    - Deterministic output
    - Safe for use inside Protein templates

    Arguments:
        text: The Markdown text to convert.
        allow_html: If True, allow raw HTML in the Markdown input.
            Default is False, which escapes HTML tags.

    Forward‑compatibility:
        This function currently assumes Markdown as the native markup format.
        Future versions may accept an explicit `format` argument to support
        additional markup languages.
    """
    mymd = make_markdown_parser()

    mymd.options["html"] = allow_html
    if not isinstance(text, str):
        raise TypeError("to_html expects a string")

    return mymd.render(text)

# ---------------------------------
# Global functions for Jinja2
# ---------------------------------
GLOBAL_CONTEXT = {
    # needed for reading environment variables
    "getenv": os.getenv, 

    # needed for accessing keyrings
    "get_password": keyring.get_password, 

    # needed for accessing operating system info (security, etc.)
    "osquery": osquery, 

    # for debugging the host environment from Protein expressions 
    "assert": jinja_assert,

    }

GLOBAL_FILTERS = {

    # needed for Jinja, to prevent interpretation of a template
    "quote": quote,

    # needed in Jinja, if the literal prefix of a template must be stripped
    # so that the string can be evaluated.
    # In Lisp, it would not be unlike the comma (,)
    "dequote": dequote, 

    # converting Markdown to HTML
    "to_html": to_html
}

GLOBAL_CONTEXT.update(GLOBAL_FILTERS)