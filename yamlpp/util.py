"""
Common utilities
"""

import os
from pathlib import Path
import ast
from typing import Any


from ruamel.yaml.error import YAMLError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from jsonschema import validate, Draft7Validator
from rich.console import Console
from rich.syntax import Syntax

from .error import YAMLValidationError, YAMLppValidationError, get_line_number

CURRENT_DIR = Path(__file__).parent 
console = Console()

# -------------------------
# Interpretation
# -------------------------
def dequote(jinja2_result:str) -> Any:
    """
    Dequote a data structure.
    In other words, it's content is deserialized (evaluated)
    """
    if not isinstance(jinja2_result, str):
        raise ValueError(f"Value passed is {type(jinja2_result).__name__} and not str.")
    return ast.literal_eval(jinja2_result)


# -------------------------
# YAML
# -------------------------
# Monkey patch CommentedMap
def getattr_patch(self, name):
    try:
        # Bypass recursion by calling dict.__getitem__
        return dict.__getitem__(self, name)
    except KeyError:
        raise AttributeError(f"Cannot find attribute '{name}'")

def setattr_patch(self, name, value):
    # Avoid clobbering internal attributes (like .ca for comments)
    if name in self.__dict__ or name.startswith('_'):
        object.__setattr__(self, name, value)
    else:
        # Write into the mapping
        dict.__setitem__(self, name, value)

# Monkey‑patch both
CommentedMap.__getattr__ = getattr_patch
CommentedMap.__setattr__ = setattr_patch


yaml_rt = YAML(typ='rt')
yaml_rt.allow_duplicate_keys = False


def load_yaml(source:str, is_text:bool=False):
    "Loads a YAML file (by default, source is a filename)"
    if is_text:
        text = source          
    else:
        filename = source
        if not os.path.isfile(filename):
            raise FileNotFoundError(f"YAML file '{filename}' does not exist")
        with open(filename, 'r', encoding="utf-8") as f:
            text = f.read()

    # create the structure
    try:
        data = yaml_rt.load(text)
    except YAMLError as e:
        raise YAMLValidationError(e)
    return text, data


  
def print_yaml(yaml_text:str):
    "Print YAML with syntax highlighting"
    syntax = Syntax(yaml_text, "yaml", line_numbers=True, theme="monokai")
    # Print with syntax highlighting
    console.print(syntax)






# -------------------------
# YAMLpp Schema Validation
# -------------------------
SCHEMA_DEFINITION = CURRENT_DIR / "yamlpp_schema.yaml"

# Load schema and initialize validator
_, schema = load_yaml(SCHEMA_DEFINITION)
validator = Draft7Validator(schema)


def validate_node(node):
    """Validate a node against jsonschema and raise YAMLppValidationError if needed."""
    print("Testing...")
    errors = sorted(validator.iter_errors(node), key=lambda e: e.path)
    if errors:
        raise YAMLppValidationError(node, errors)
    else:
        print("No validation errors found.")









