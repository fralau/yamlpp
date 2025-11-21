"""
Common utilities
"""

import os
from pathlib import Path
# import yaml
from ruamel.yaml import YAML
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
import ast
from typing import Any
from jsonschema import validate, Draft7Validator

CURRENT_DIR = Path(__file__).parent 

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

yaml = YAML(typ='rt')


def load_yaml(filename:str):
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"YAML file '{filename}' does not exist")
    with open(filename, 'r', encoding="utf-8") as f:
        text = f.read()          # <-- raw YAML string
    data = yaml.load(text)       # <-- parsed object
    assert type(data) not in (dict, list)
    # print("*** Imported type:", type(data).__name__)
    return text, data


  


def get_line_number(yaml_obj):
    """
    Return the first line number (1-based) for a ruamel.yaml object.
    Works with CommentedMap, CommentedSeq, and CommentedScalar.
    """
    # Case 1: Mapping → take the first key
    if isinstance(yaml_obj, CommentedMap):
        if hasattr(yaml_obj, 'lc') and yaml_obj.lc.data:
            first_key = next(iter(yaml_obj.lc.data))
            return yaml_obj.lc.data[first_key][0] + 1

    # Case 2: Sequence → take the first index
    elif isinstance(yaml_obj, CommentedSeq):
        if hasattr(yaml_obj, 'lc') and yaml_obj.lc.data:
            if 0 in yaml_obj.lc.data:
                return yaml_obj.lc.data[0][0] + 1

    # Case 3: Scalar → direct line
    elif hasattr(yaml_obj, 'lc') and yaml_obj.lc.line is not None:
        return yaml_obj.lc.line + 1

    # Fallback: no line info
    print(f"Cannot find line number on {type(yaml_obj)}")
    return None



# -------------------------
# YAMLpp Schema Validation
# -------------------------
SCHEMA_DEFINITION = CURRENT_DIR / "yamlpp_schema.yaml"

# Load schema and initialize validator
_, schema = load_yaml(SCHEMA_DEFINITION)
validator = Draft7Validator(schema)

class YAMLppValidationError(Exception):
    """
    Custom exception tied to a Ruamel YAML node.
    Extracts line number directly from the node and prints a concise message.
    """
    def __init__(self, line_no: int, message: str):
        self.line_no = line_no
        self.message = message
        super().__init__(f"Line {self.line_no}: {self.message}")

    def __str__(self):
        return f"Line {self.line_no}: {self.message}"


def get_subnode(tree, path):
    """Walk the YAML tree to extract the sub-node at the given error path."""
    from functools import reduce
    import operator
    try:
        return reduce(operator.getitem, path, tree)
    except Exception:
        return tree  # fallback to root if path lookup fails


def format_error(error):
    """Format a jsonschema.ValidationError with path, description, and allowed keys."""
    path = ".".join(str(p) for p in error.path)
    desc = error.schema.get("description", "")

    # Build a clean message
    if error.validator == "oneOf":
        # Summarize instead of dumping the whole node
        raw = "Value does not match any of the expected node types"
        if error.context:
            # Collect suberror messages (without values)
            details = "; ".join(se.message.split(" ")[0] for se in error.context)
            raw = f"{raw}. Details: {details}"
    elif error.validator == "additionalProperties":
        # Show which property was invalid and what keys are allowed
        invalid = error.message.split("'")[1]  # extract offending key
        allowed = ", ".join(error.schema.get("properties", {}).keys())
        raw = f"Unexpected property '{invalid}'. Allowed keys: {allowed}"
    else:
        # Fallback: use validator name instead of full dump
        raw = f"{error.validator} validation failed"

    if path:
        return f"Validation error at {path}: {raw} {desc}".strip()
    else:
        return f"Validation error: {raw} {desc}".strip()




def validate_node(node):
    """Validate a node against jsonschema and raise YAMLppValidationError if needed."""
    print("Testing...")
    errors = sorted(validator.iter_errors(node), key=lambda e: e.path)
    if errors:
        for error in errors:
            subnode = get_subnode(node, error.path)
            line_no = get_line_number(subnode)
            msg = format_error(error)
            raise YAMLppValidationError(line_no, msg)
    else:
        print("No validation errors found.")


