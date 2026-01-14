"""
Utilities for facilitating testing
"""

import inspect
from string import Template
from pathlib import Path

# ----------------------------------------------
# Import from other places in Protein
# ----------------------------------------------
from protein.core import protein_comp
from protein.util import print_yaml

# ----------------------------------------------
# Testing utilities
# ----------------------------------------------
def interp(text):
    """
    Interpolate a string using the caller's scope, using the $ syntax
    from the standard library's `string.Template`.

    This is useful for embedding initial values in Protein programs,
    in a way that does _not_ interfere with Protein's own templating (Jinja)

    For example:
        NAME = "Joe Bloggs"
        program = interp("Hello $NAME")
    """
    frame = inspect.currentframe().f_back
    scope = {}
    scope.update(frame.f_globals)
    scope.update(frame.f_locals)
    return Template(text).substitute(scope)

def read_file(filepath:str) -> str:
    """
    Read the contents of a file and return as a string.
    """
    assert Path(filepath).is_file(), f"File not found: {filepath}"
    with open(filepath, 'r') as f:
        return f.read() 