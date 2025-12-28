"""
Test the Stack class
"""
import pytest
from yamlpp.stack import Stack


def test_multiple_pushes_and_overrides():
    """Pushing multiple scopes should allow later scopes to override earlier values.
    This validates the 'last write wins' semantics of merged dictionaries.
    """
    s = Stack({"x": 1, "y": 2})
    s.push({"y": 99, "z": 3})
    s.push({"z": 42, "w": 5})
    # 'y' overridden by second scope
    assert s["y"] == 99
    # 'z' overridden by third scope
    assert s["z"] == 42
    # 'x' remains from base
    assert s["x"] == 1
    # 'w' only in top scope
    assert s["w"] == 5
    assert len(s) == 4


def test_combination_of_setitem_and_push():
    """Mixing direct assignment with pushes should still respect top-scope precedence.
    Ensures that __setitem__ modifies only the current scope, not historical ones.
    """
    s = Stack({"a": 1})
    s["a"] = 2
    s.push({"a": 3})
    assert s["a"] == 3
    # After popping, assignment from earlier scope should reappear
    s.pop()
    assert s["a"] == 2


def test_combination_of_delitem_and_override():
    """Deleting a key from the top scope should expose the value from a lower scope.
    Validates that deletion only removes the top layer, not the merged view entirely.
    """
    s = Stack({"k": "base"})
    s.push({"k": "override"})
    assert s["k"] == "override"
    del s["k"]
    # Now the base value should be visible again
    assert s["k"] == "base"


def test_push_pop_sequence_complex():
    """A sequence of pushes and pops should correctly restore previous merged states.
    This checks stack discipline across multiple operations.
    """
    s = Stack({"a": 1})
    s.push({"b": 2})
    s.push({"c": 3})
    assert set(s.copy().keys()) == {"a", "b", "c"}
    s.pop()
    assert set(s.copy().keys()) == {"a", "b"}
    s.pop()
    assert set(s.copy().keys()) == {"a"}


def test_iter_and_len_after_complex_operations():
    """Iteration and length should always reflect the current merged state,
    even after multiple pushes, overrides, and deletions.
    """
    s = Stack({"x": 1})
    s.push({"y": 2})
    s["z"] = 3
    del s["y"]
    keys = list(iter(s))
    assert set(keys) == {"x", "z"}
    assert len(s) == 2

def test_general_1():
    """
    Simple test with pushs and pop

    - allocation
    - operator in
    - values() method
    """
    s = Stack({'foo': 0, 'bar': 0, 'baz': 0})
    s.push({'bar': 1, 'baz': 1})
    s.push({'baz': 2})

    assert len(s) == 3
    assert s['foo'] == 0
    assert s['bar'] == 1
    assert s['baz'] == 2
    assert 'foo' in s
    assert sum([v for v in s.values()]) == 3
    
    s.pop()
    assert len(s) == 3
    assert s['foo'] == 0
    assert s['bar'] == 1
    assert s['baz'] == 1
    assert 'foo' in s
    assert sum([v for v in s.values()]) == 2

    s.pop()
    assert len(s) == 3
    assert s['foo'] == 0
    assert s['bar'] == 0
    assert s['baz'] == 0
    assert 'foo' in s
    assert sum([v for v in s.values()]) == 0


# --------------------------
# Test merging
# --------------------------


def test_simple_merge_overrides_scalar():
    """Verify that when two scopes define the same scalar key,
    the later scope overrides the earlier one."""
    s = Stack()
    s.push({"a": 1})
    s.push({"a": 2})
    merged = s._merged()
    assert merged == {"a": 2}


def test_nested_dicts_are_merged():
    """Ensure that nested dictionaries are merged recursively,
    preserving earlier keys while adding new ones from later scopes."""
    s = Stack()
    s.push({"db": {"host": "localhost", "port": 5432}})
    s.push({"db": {"user": "admin"}})
    merged = s._merged()
    assert merged["db"]["host"] == "localhost"
    assert merged["db"]["port"] == 5432
    assert merged["db"]["user"] == "admin"


def test_lists_are_replaced_not_concatenated():
    """Confirm that lists are replaced by later scopes rather than concatenated,
    so the newer list completely overrides the older one."""
    s = Stack()
    s.push({"items": ["a", "b"]})
    s.push({"items": ["c"]})
    merged = s._merged()
    assert merged["items"] == ["c"]


def test_multiple_scopes_merge_correctly():
    """Check that multiple scopes merge correctly, with scalars overridden,
    nested dicts merged, and later values taking precedence."""
    s = Stack()
    s.push({"x": 1, "nested": {"a": 10}})
    s.push({"y": 2, "nested": {"b": 20}})
    s.push({"nested": {"a": 99}})
    merged = s._merged()
    assert merged["x"] == 1
    assert merged["y"] == 2
    assert merged["nested"]["a"] == 99
    assert merged["nested"]["b"] == 20


def test_cache_is_reused_until_dirty():
    """Verify that the merged result is cached and reused until the stack
    is marked dirty, at which point a new merge is performed."""
    s = Stack()
    s.push({"a": 1})
    first = s._merged()
    second = s._merged()
    assert first is second  # same cached object
    s.push({"a": 2})
    third = s._merged()
    assert third is not first
    assert third["a"] == 2
