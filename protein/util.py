"""
Common utilities
"""

import os
from pathlib import Path
import string
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

from .error import YAMLValidationError, YAMLppValidationError, GeneralYAMLppError
from .dotenv import DotEnv

# -------------------------
# Initialization
# -------------------------
CURRENT_DIR = Path(__file__).parent 
console = Console()

# file formats/extensions
# ypp format is considered here equivalent to yaml (to facilitate .load)
FILE_FORMATS = ['yaml', 'json', 'toml', 'python', 'ypp', 'env']

# The prefix that marks a string as literal (not to be interpreted by Protein)
LITERAL_PREFIX = "#!literal"

def strip_prefix(s: str, prefix=LITERAL_PREFIX) -> str:
    """
    If the string starts with the prefix, strip it and return the rest"
    (by default, uses the literal prefix).
    """
    if isinstance(s, str) and s.startswith(prefix):
        return s[len(prefix):].lstrip()
    return s


# -------------------------
# OS
# -------------------------
from pathlib import Path

def safe_path(root: str | Path, pathname: str | Path) -> Path:
    """
    Resolve a pathname relative to a root and:
    - enforce sandboxing (forbid absolute paths, enforce containment), 
    - verify existence of file
    """
    root = Path(root).resolve()
    pathname = Path(pathname)

    # 1. Absolute paths are forbidden
    if pathname.is_absolute():
        raise FileNotFoundError(f"Absolute path not allowed: {pathname}")

    # 2. Resolve inside root
    candidate = (root / pathname).resolve()

    # 3. Enforce containment
    if root not in candidate.parents and candidate != root:
        raise FileNotFoundError(f"Path {pathname} escapes root {root}")

    # 4. Enforce existence
    if not candidate.exists():
        raise FileNotFoundError(f"Path does not exist: {candidate}")

    return candidate

def get_full_filename(source_dir:str, filename:str) -> str:
    "Get the full filename, making sure that it exists"
    full_filename = Path(source_dir) / filename
     # ✅ Ensure the parent directory exists (CI-safe)
    Path(full_filename).parent.mkdir(parents=True, exist_ok=True)
    return full_filename

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
    "Implement dot notation (reading), to help testing"
    try:
        # Bypass recursion by calling dict.__getitem__
        return dict.__getitem__(self, name)
    except KeyError:
        raise AttributeError(f"Cannot find attribute '{name}'")

def setattr_patch(self, name, value):
    "Implement dot notation (writing), to help testing"
    # Avoid clobbering internal attributes (like .ca for comments)
    if name in self.__dict__ or name.startswith('_'):
        object.__setattr__(self, name, value)
    else:
        # Write into the mapping
        dict.__setitem__(self, name, value)

def repr_patch(self):
    "Structural repr: show first 3 items and always the last one"
    items = list(self.items())
    n = len(items)

    if n <= 4:
        # Small map: show everything
        return f"<Map {items}>"

    # Large map: show head and tail
    head = items[:3]
    tail = items[-1]
    return f"<Map {head} ... {tail}>"



CommentedMap.__getattr__ = getattr_patch
CommentedMap.__setattr__ = setattr_patch
CommentedMap.__repr__    = repr_patch
CommentedMap.is_patched = True # confirm it is patched.




def collapse_seq(seq:collections.abc.Sequence):
    """
    Collapse a list (sequence); a key component of YAMLpp semantics.

    It is what makes loops return expected items.

    - A sequence of 0 returns None
    - A sequence of 1 returns the element (unless keep_singleton=True).
    - Otherwise, no collapse
    """
   # print("Collapse...")
    if not isinstance(seq, collections.abc.Sequence):
        raise ValueError(f"Cannot collapse, this is not a sequence: {seq}")
    if len(seq) == 0:
        return None
    elif len(seq) == 1:
        r = seq[0]
        # print("...sequence of length 1:", seq, '=>', r)
        # singletons (lists of one) are unpacked; 
        return r
    else:

        # if all(isinstance(x, collections.abc.Seq) and len(x) == 1 for x in seq):
        #     return [x[0] for x in seq]

        # "Return the list":
        return seq


def collapse_maps(seq:collections.abc.Sequence):
    "Collapse all the maps in a sequence"
    if all(
        isinstance(x, collections.abc.Mapping) and len(x) == 1
        for x in seq):
        # this is the case of a list containing 1 mapping each
        result = {}
        for el in seq:
            # print("Element:", el)
            key, value = next(iter(el.items()))
            result[key] = value
        return result
    else:
        return seq

# Global reusable round-trip YAML instance, using ruamel defaults
class ImmutableYAML(YAML):
    "An locked-down Ruamel class"
    def __init__(self, *args, **kwargs):
        self._locked = False
        super().__init__(*args, **kwargs)
        super().__setattr__('allow_duplicate_keys', False)
        self._locked = True

    def __setattr__(self, name, value):
        # allow ruamel internals
        if name in {"Reader", "Scanner", "Parser", "Composer",
                    "Constructor", "Resolver", 'tags', 'version'} or name[0] == '_':
            super().__setattr__(name, value)
            return
        if getattr(self, "_locked", False):
            raise AttributeError(f"ImmutableYAML is locked: cannot set {name}")
        super().__setattr__(name, value)

YAML_RT = ImmutableYAML(typ='rt')



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
        data = YAML_RT.load(text)
    except YAMLError as e:
        raise YAMLValidationError(e)
    return text, data

YAML_SAFE = ImmutableYAML(typ='safe')

def parse_yaml(source: str) -> Any:
    "Loads YAML in a safe way (useful for parsing snippets)"
    try:
        return YAML_SAFE.load(source)
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




def get_format(filename: str, format:str=None) -> str:
    """
    Get the file format of a file, from its filename or explicit format specification.

    Rules:

    1. Use the format parameter, or
    2. Use the filename extension.

    The format must be in the list of supported file formats.
    """
    if format and not isinstance(format, str):
        raise TypeError(f"Format, if specified, must be a string, not a {type(format).__name__}: {format}")
    if format:
        ext = format.lower()
    else:
        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        if not ext:
            raise ValueError(f"Cannot determine format for '{filename}'")
    if ext not in FILE_FORMATS:
        raise ValueError(f"Format '{ext}' is unsupported; supported: {FILE_FORMATS}")
    return ext




def literal_str_representer(representer, data):
    "YAML Representer for strings (which excludes literal strings"
    if isinstance(data, str) and data.startswith(LITERAL_PREFIX):
        data = data[len(LITERAL_PREFIX):].lstrip()
    return representer.represent_str(data)

def to_yaml(
    node,
    *,
    indent: int | None = None,
    offset: int | None = None,
    explicit_start: bool | None = None,
    explicit_end: bool | None = None,
    allow_unicode: bool | None = None,
    canonical: bool | None = None,
    width: int | None = None,
    preserve_quotes: bool | None = None,
    typ: str | None = None,
    pure: bool | None = None,
    version: tuple[int, int] | None = None,
) -> str:
    """
    Serialize a Python object or ruamel.yaml node to a YAML string.

    If all arguments are None, reuse the global `YAML_RT` instance.
    Otherwise, create a new YAML object and apply only the arguments
    explicitly provided. Defaults are left to ruamel.yaml itself.
    """
    if all(arg is None for arg in (
        indent, offset, explicit_start, explicit_end, allow_unicode,
        canonical, width, preserve_quotes, typ, pure, version
    )):
        yaml = YAML_RT
    else:
        yaml = YAML(typ=typ or "rt", pure=pure)
        yaml.allow_duplicate_keys = False
        if version is not None:
            yaml.version = version
        if indent is not None:
            yaml.indent(mapping=indent, sequence=indent)
        if offset is not None:
            yaml.indent(offset=offset)
        if explicit_start is not None:
            yaml.explicit_start = explicit_start
        if explicit_end is not None:
            yaml.explicit_end = explicit_end
        if allow_unicode is not None:
            yaml.allow_unicode = allow_unicode
        if canonical is not None:
            yaml.canonical = canonical
        if width is not None:
            yaml.width = width
        if preserve_quotes is not None:
            yaml.preserve_quotes = preserve_quotes


    yaml.representer.add_representer(str, literal_str_representer)

    stream = StringIO()
    yaml.dump(node, stream)
    return stream.getvalue()






def normalize(node):
    """
    Recursively convert a ruamel.yaml round-trip tree ('rt') 
    into plain dicts, lists, and scalars.

    NOTE: Ruamel produces a tree with additional directed edges (from aliases to anchors). What you get is a directed graph. YAMLpp "does nothing" with anchors and aliases. It just leaves them where they are. But when you export to other formats than YAML, you need to resolve them.

    This function ensures that YAML anchors (&...), aliases(*...),
    and Ruamel-specific wrappers are removed.

    That's the correct way to make sure that the tree can be exported
    to a koine for other formats.
    """
    if isinstance(node, (ScalarString, str)):
        # unwrap ruamel scalar wrappers (e.g. DoubleQuotedScalarString)
        r = str(node)
        # remove literal prefix if any
        if r.startswith(LITERAL_PREFIX):
            r = r[len(LITERAL_PREFIX):].lstrip()
        return r
    elif isinstance(node, (int, float, bool)) or node is None:
        return node
    elif isinstance(node, collections.abc.Mapping):
        return {str(k): normalize(v) for k, v in node.items()}
    elif isinstance(node, collections.abc.Sequence):
        assert not (isinstance(node, str))
        return [normalize(v) for v in node]
    else:
        # fallback: try to coerce to string
        return str(node)




def to_toml(tree, **kwargs) -> str:
    """
    Convert a ruamel.yaml tree into a TOML string.
    """
    plain = normalize(tree)
    return tomlkit.dumps(plain, **kwargs)


def to_json(tree, **kwargs) -> str:
    """
    Convert a ruamel.yaml tree into a TOML string.
    """
    plain = normalize(tree)
    s = json.dumps(plain, **kwargs)
    json.loads(s)
    return s

def to_python(tree):
    """
    Convert a ruamel.yaml tree into a TOML string.

    No arguments
    """
    plain = normalize(tree)
    # return pprint.pformat(plain, indent=2, width=80)
    return repr(plain)



DEFAULT_COMMENT_BLOCK = "# File automatically generated by YAMLPP"

def to_comment_block(text: str) -> str:
    """
    Convert a multiline string into a block of comment lines,
    each starting with '# '.
    """
    if not text:
        return DEFAULT_COMMENT_BLOCK
    return "\n".join(f"# {line}" if line.strip() else "#" for line in text.splitlines())




CONV_FORMATS = {
    'yaml'   : to_yaml,
    'json'   : to_json,
    'python' : to_python,
    'toml'   : to_toml,
    'ypp'    : to_yaml, # it's a pure alias of yaml
    'env' : DotEnv.dumps,
}

NO_COMMENTS = ['json'] # no comments allowed

def serialize(tree, format:str='yaml', comment:str=None, **kwargs) -> str:
    """
    General serialization function with format.

    Calls the appropriate function.

    Unsupported kwargs will raise a KeyError.
    """
    kwargs = kwargs or {}
    if format:
        format = format.lower()
    else: 
        format = 'yaml'
    func = CONV_FORMATS.get(format)
    if func is None:
        raise ValueError(f"Unsupported format {format}")
    try:
        r = func(tree, **kwargs)
        if format in NO_COMMENTS:
            return r
        else:
            # Add the comment on top
            comment = to_comment_block(comment)
            return "\n".join((comment, r))
    except TypeError as e:
        raise KeyError(f"Error in additional arguments for conversion to '{format}': {kwargs}\n{e}")

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
    if format in ("yaml", 'ypp'):
        # they are equivalent
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
    elif format == "env":
        return DotEnv.loads(text)
    else:
        raise ValueError(f"Unsupported format: {format}")

# -------------------------
# YAMLpp Schema Validation
# -------------------------
SCHEMA_DEFINITION = CURRENT_DIR / "protein_schema.yaml"

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


# -------------------------
# Other
# -------------------------
def check_name(name:str) -> None:
    """
    Check 
    """
    if not name:
        raise ValueError("Name is empty")
    elif not name.isidentifier:
        raise ValueError(f"Name '{name}' is not a valid identifier")
    # pass




def extract_identifier(path):
    """
    Extrait un identifiant Python valide à partir d'un chemin.
    Transformations minimales :
      - remplace les espaces par '_'
      - remplace les caractères non autorisés par '_'
      - préfixe '_' si le nom commence par un chiffre
    Lève ValueError si le résultat n'est toujours pas un identifiant valide.
    """
    p = Path(path)
    name = p.stem

    # Remplacer explicitement les espaces
    name = name.replace(" ", "_")

    # Si déjà valide, on retourne tel quel
    if name.isidentifier():
        return name

    allowed = string.ascii_letters + string.digits + "_"

    # Remplacement minimal : tout ce qui n'est pas autorisé → '_'
    transformed = "".join(c if c in allowed else "_" for c in name)

    # Si ça commence par un chiffre → préfixer '_'
    if transformed and transformed[0].isdigit():
        transformed = "_" + transformed

    # Nettoyage minimal : éviter les underscores vides
    transformed = transformed.strip("_")

    # Vérification finale
    if transformed and transformed.isidentifier():
        return transformed

    raise ValueError(
        f"Impossible de dériver un identifiant Python valide à partir de '{name}'. "
        f"Résultat obtenu : '{transformed}'"
    )


