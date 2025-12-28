"""
Errors
"""
from enum import Enum

from ruamel.yaml.comments import CommentedMap, CommentedSeq


class GeneralYAMLppError(Exception):
    """
    General YAML exception
    """
    def __init__(self, line_no:int, err_type: str, message: str):
        self.line_no = line_no
        self.err_type = err_type
        if not isinstance(message, str):
            message = str(message)
        self.message = message
        super().__init__(self.__str__())

    def __str__(self):
        return (f"[{self.err_type}] Line {self.line_no}: {self.message}")

# --------------------------
# Validation Errors
# --------------------------
class YAMLValidationError(GeneralYAMLppError):
    """
    Custom exception tied to the loading process of Ruamel
    Extracts line number directly from the node and prints a concise message.
    """
    def __init__(self, e, prefix:str=''):
        line_no = e.problem_mark.line + 1 
        message = f"{prefix} {e}"
        err_type = type(e).__name__
        super().__init__(line_no, err_type, message)

class YAMLppValidationError(GeneralYAMLppError):
    """
    Validation Error (jsonschema)
    """
    def __init__(node, errors):
        for error in errors:
            subnode = get_subnode(node, error.path)
            line_no = get_line_number(subnode)
            message = format_error(error)
            err_type = "JsonSchemaError"
            super().__init__(line_no, err_type, message)     

def get_line_number(yaml_obj):
    """
    Return the first line number (1-based) for a ruamel.yaml object.
    Works with CommentedMap, CommentedSeq, and CommentedScalar.
    """

    
    # Case 1: Mapping → take the first key
    # NOTE: lines start from 0, so we should add + 1; but we need to take the Parent (-1) 
    if isinstance(yaml_obj, CommentedMap):
        if hasattr(yaml_obj, 'lc') and yaml_obj.lc.data:
            first_key = next(iter(yaml_obj.lc.data))
            return yaml_obj.lc.data[first_key][0] + 1 -1

    # Case 2: Sequence → take the first index
    # NOTE: lines start from 0, so we should add + 1; but we need to take the Parent (-1) 
    elif isinstance(yaml_obj, CommentedSeq):
        if hasattr(yaml_obj, 'lc') and yaml_obj.lc.data:
            if 0 in yaml_obj.lc.data:
                return yaml_obj.lc.data[0][0] + 1 -1

    # Case 3: Scalar → direct line
    # NOTE: lines start from 0, so we should add + 1;
    elif hasattr(yaml_obj, 'lc') and yaml_obj.lc.line is not None:
        return yaml_obj.lc.line + 1

    # Fallback: no line info
    print(f"Cannot find line number on {type(yaml_obj)}")
    return None



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
 
# --------------------------
# YAMLpp Error
# --------------------------

class Error(str, Enum):
    VALIDATION = "ValidationError"
    KEY = "KeyNotFound"
    INDEX = "IndexNotFound"
    ARGUMENTS = "ArgumentMismatch"
    FILE = "FileError"
    EXPRESSION = "ExpressionError"
    SQL = "SQLError"
    VALUE = "ValueError"
    TYPE = "TypeError"
    OTHER = "OtherError"
    # add more categories as needed

    def __str__(self):
        return self.value

class YAMLppError(GeneralYAMLppError):
    """
    Custom exception connected to the YAMLpp algorithm.
    Extracts line number and line text directly from the node.
    """
    def __init__(self, node, err_type: Error, message: str):
        if isinstance(node, (CommentedMap, CommentedSeq)):
            line_no = get_line_number(node) 
        else:
            line_no = 0
        self.line_no = line_no
        self.node = node
        self.err_type = err_type
        self.message = message
        super().__init__(line_no, err_type, message)



# --------------------------
# Lower Level Errors
# --------------------------

class DispatcherError(Exception):
    "Error raised by the despatcher"
    def __init__(self, err_type: Error, message: str):
        self.err_type = err_type
        self.message = str(message)
        super().__init__(str(self))

    def __str__(self):
        return f"[{self.err_type}] {self.message}"
   



class JinjaExpressionError(Exception):
    "An Expression error that must be caught later, at first opportunity"
    def __init__(self, expression:str, error:Exception):
        self.expression = expression
        self.err_type = type(error).__name__
        self.error_text = str(error) 

    def __str__(self):
        return (f"Expression '{self.expression}'\n{self.err_type}:{self.error_text}")