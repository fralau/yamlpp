"""
Tests for Interpreter.handle_binding()

These tests verify:
- valid return types (scalar, sequence, mapping)
- invalid return types (custom objects, generators)
- argument shape rules (.args, .kwargs, positional, keyword)
- error handling for malformed arguments
- callable lookup and type validation

Note that the representation of 'f' in the stack is '.f' at the level of the entry.
"""

import pytest
from protein import Interpreter
from protein.core import MappingEntry


def entry_with_value(v):
    """Helper to build a MappingEntry with a fixed key."""
    return MappingEntry(key='.f', value=v)


# ------------------------------------------------------------
# Valid return types
# ------------------------------------------------------------

def test_callable_returns_scalar():
    """A callable returning a scalar must be accepted."""
    i = Interpreter()
    i.stack['f'] = lambda: 42
    print("Stack f is:", i.stack['f'])
    assert i.stack['f']() == 42

    entry = entry_with_value({})
    assert i.handle_binding('.f', entry) == 42


def test_callable_returns_list():
    """A callable returning a Python list must be accepted as a sequence."""
    i = Interpreter()
    i.stack['f'] = lambda: [1, 2, 3]
    entry = entry_with_value({})
    assert i.handle_binding('.f', entry) == [1, 2, 3]


def test_callable_returns_dict():
    """A callable returning a Python dict must be accepted as a mapping."""
    i = Interpreter()
    i.stack['f'] = lambda: {'a': 1}
    entry = entry_with_value({})
    assert i.handle_binding('.f', entry) == {'a': 1}


def test_object_variable():
    """If the stack entry is not callable, the value is returned (if correct)."""
    i = Interpreter()
    i.stack['f'] = 123
    entry = entry_with_value({})
    assert i.handle_binding('.f', entry) == 123

# ------------------------------------------------------------
# Invalid return types
# ------------------------------------------------------------

def test_callable_returns_invalid_type():
    """A callable returning a non-node type must raise a TYPE error."""
    class X: pass
    i = Interpreter()
    i.stack['f'] = lambda: X()
    entry = entry_with_value({})
    with pytest.raises(Exception):
        i.handle_binding('.f', entry)


def test_callable_returns_generator():
    """Generators are not valid Protein node types and must be rejected."""
    i = Interpreter()
    i.stack['f'] = lambda: (x for x in range(3))
    entry = entry_with_value({})
    with pytest.raises(Exception):
        i.handle_binding('.f', entry)


# ------------------------------------------------------------
# Argument shapes
# ------------------------------------------------------------

def test_positional_args():
    """A bare sequence must be interpreted as positional arguments."""
    i = Interpreter()
    i.stack['f'] = lambda x, y: x + y
    entry = entry_with_value([2, 3])
    assert i.handle_binding('.f', entry) == 5


def test_keyword_args():
    """A bare mapping must be interpreted as keyword arguments."""
    i = Interpreter()
    i.stack['f'] = lambda x, y: x + y
    entry = entry_with_value({'x': 2, 'y': 3})
    assert i.handle_binding('.f', entry) == 5


def test_args_kwargs_form():
    """.args and .kwargs must be combined into positional and keyword arguments."""
    i = Interpreter()
    i.stack['f'] = lambda x, y: x + y
    entry = entry_with_value({
        '.args': [2],
        '.kwargs': {'y': 3},
    })
    assert i.handle_binding('.f', entry) == 5





# ------------------------------------------------------------
# Argument shape errors
# ------------------------------------------------------------

def test_args_not_sequence():
    """.args must be a sequence; any other type must raise an error."""
    i = Interpreter()
    i.stack['f'] = lambda: None
    entry = entry_with_value({'.args': 123})
    with pytest.raises(Exception):
        i.handle_binding('.f', entry)


def test_kwargs_not_mapping():
    """.kwargs must be a mapping; any other type must raise an error."""
    i = Interpreter()
    i.stack['f'] = lambda: None
    entry = entry_with_value({'.kwargs': 123})
    with pytest.raises(Exception):
        i.handle_binding('.f', entry)


# ------------------------------------------------------------
# Callable lookup errors
# ------------------------------------------------------------

def test_callable_not_found():
    """Calling a missing name must raise a KEY error."""
    i = Interpreter()
    entry = entry_with_value({})
    with pytest.raises(Exception):
        i.handle_binding('missing', entry)



