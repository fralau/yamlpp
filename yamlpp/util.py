"""
Common utilities
"""

import os
from pathlib import Path
import ast
from typing import Any
import collections
from io import StringIO
import json


from ruamel.yaml.error import YAMLError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import ScalarString

from jsonschema import validate, Draft7Validator
from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text
import tomlkit
import pprint

from .error import YAMLValidationError, YAMLppValidationError, GeneralYAMLppError

CURRENT_DIR = Path(__file__).parent 
console = Console()

FILE_FORMATS = ['yaml', 'json', 'toml', 'python']
# -------------------------
# OS
# -------------------------
from pathlib import Path

def safe_path(root: str|Path, pathname: str) -> Path:
    """
    Get a pathname relative to a root, ensure it cannot escape,
    and verify that it exists.
    """
    if isinstance(root, str):
        root = Path(root)
    candidate = (root / pathname).resolve()

    # check that candidate is inside root
    if root not in candidate.parents and candidate != root:
        raise FileNotFoundError(f"Path {pathname} cannot be higher than {root}")

    # check that candidate exists
    if not candidate.exists():
        raise FileNotFoundError(f"Path {candidate} does not exist")

    return candidate



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


def load_yaml(source:str, is_text:bool=False) -> tuple[str, Any]:
    """
    Loads a YAML file (by default, source is a filename), in a round-trip way.
    Returns both the text and the tree.
    """
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

yaml_safe = YAML(typ='safe')

def parse_yaml(source: str) -> Any:
    "Loads YAML in a safe way (useful for parsing snippets)"
    try:
        return yaml_safe.load(source)
    except YAMLError as e:
        raise YAMLValidationError(e, prefix=f"Incorrect input: {source}\n")


  
def print_yaml(yaml_text: str, filename: str | Path | None = None):
    """Print YAML with syntax highlighting, optionally showing filename."""
    if filename is not None:
        text = Text(f"File: {filename}", style="green")
        console.print(text)
    syntax = Syntax(yaml_text, "yaml", line_numbers=True, theme="monokai")
    console.print(syntax)







# -------------------------
# Serialization formats
# -------------------------

def to_yaml(node) -> str:
    """
    Translate a tree into a YAML string.

    It's the pure Ruamel function.
    """
    buff = StringIO()
    yaml_rt.dump(node, buff)
    return buff.getvalue()




def flatten(node):
    """
    Recursively convert a ruamel.yaml round-trip tree ('rt') 
    into plain dicts, lists, and scalars.

    NOTE: Ruamel produces a tree with additional directed edges (from aliases to anchors). What you get is a directed graph. YAMLpp "does nothing" with anchors and aliases. It just leaves them where they are. But when you export to other formats than YAML, you need to resolve them.

    This function ensures that YAML anchors (&...), aliases(*...),
    and Ruamel-specific wrappers are removed.

    That's the correct way to make sure that the tree can be exported
    to a koine for other formats.
    """
    if isinstance(node, ScalarString):
        # unwrap ruamel scalar wrappers (e.g. DoubleQuotedScalarString)
        return str(node)
    elif isinstance(node, (str, int, float, bool)) or node is None:
        return node
    elif isinstance(node, collections.abc.Mapping):
        return {str(k): flatten(v) for k, v in node.items()}
    elif isinstance(node, collections.abc.Sequence):
        assert not (isinstance(node, str))
        return [flatten(v) for v in node]
    else:
        # fallback: try to coerce to string
        return str(node)




def to_toml(tree) -> str:
    """
    Convert a ruamel.yaml tree into a TOML string.
    """
    plain = flatten(tree)
    return tomlkit.dumps(plain)


def to_json(tree) -> str:
    """
    Convert a ruamel.yaml tree into a TOML string.
    """
    plain = flatten(tree)
    s = json.dumps(plain, indent=2)
    json.loads(s)
    return s

def to_python(tree):
    """
    Convert a ruamel.yaml tree into a TOML string.
    """
    plain = flatten(tree)
    # return pprint.pformat(plain, indent=2, width=80)
    return str(plain)

CONV_FORMATS = {
    'yaml'   : to_yaml,
    'json'   : to_json,
    'python' : to_python,
    'toml'   : to_toml
}

def serialize(tree, format:str='yaml') -> str:
    """
    General serialization function with format
    """
    if format:
        format = format.lower()
    else: 
        format = 'yaml'
    func = CONV_FORMATS.get(format)
    if func is None:
        return ValueError(f"Unsupported format {format}")
    return func(tree)

def deserialize(text: str, format: str='yaml', *args, **kwargs):
    """
    Parse text back into Python objects depending on format.
    Supported: yaml, json, toml, python
    Extra args/kwargs are passed to the backend parser.

    YAML: by default the deserialization is 'rt' (round-trip);
    if you want to change it (to strip comments, etc.), use 'safe'.
    """
    DEFAULT_YAML = 'rt'
    if format:
        format = format.lower()
    else: 
        format = 'yaml'
    if format == "yaml":
        if args is None and kwargs is None:
            return parse_yaml(text)
        else:
            typ = kwargs.pop('typ', DEFAULT_YAML)
            y = YAML(typ=typ)
            return y.load(text, *args)
    elif format == "json":
        return json.loads(text, *args, **kwargs)
    elif format == "toml":
        return tomlkit.loads(text, *args, **kwargs)
    elif format == "python":
        return ast.literal_eval(text)
    else:
        raise ValueError(f"Unsupported format: {format}")

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









