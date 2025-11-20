"""
Common utilities
"""

import os
# import yaml
from ruamel.yaml import YAML
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
import ast
from typing import Any



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
    return None



