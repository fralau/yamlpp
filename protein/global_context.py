"""
Defining the GLOBAL context for a Protein interpreter.

NOTE:
    What we define as "global" is not the same as in most languages.
    It is simply a part of the first frame on the lexical stack,
    which contains necessary functions.

    (It is on top of the Jinja2 utilities.)
"""

import os

import keyring

from .sql import osquery
from .util import strip_prefix



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

    # needed in Jinja, if the literal prefix of a template must be stripped
    # so that the string can be evaluated.
    # In Lisp, it would not be unlike the comma (,)
    "dequote": strip_prefix, 

    # for debugging the host environment from Protein expressions 
    "assert": jinja_assert
    }