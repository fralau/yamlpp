"""
Test suite for the deterministic text rendering engine.

These tests validate:
- indentation inference
- explicit indentation shifts
- implicit indentation propagation
- shift-signal handling (". ")
- multiline rendering
- deterministic output
"""

import pytest
from yamlpp.buffer import Indentation, infer_indent_level, render_buffer


# -------------------------
# infer_indent_level tests
# -------------------------

def test_infer_indent_level_empty():
    """infer_indent_level should return 0 for an empty string."""
    assert infer_indent_level("", 2) == 0


def test_infer_indent_level_single_line():
    """infer_indent_level should compute indentation from leading spaces."""
    assert infer_indent_level("    hello", 2) == 2


def test_infer_indent_level_multiline():
    """infer_indent_level should use the last line of a multiline string."""
    s = "line1\n  line2\n    line3"
    assert infer_indent_level(s, 2) == 2


def test_infer_indent_level_no_indent():
    """infer_indent_level should return 0 when no leading spaces exist."""
    assert infer_indent_level("hello", 4) == 0


# -------------------------
# render_buffer basic tests
# -------------------------

def test_render_single_line_no_indent():
    """render_buffer should emit a single line without indentation."""
    out = render_buffer(["hello"], indent_width=2)
    assert out == "hello"


def test_render_ignores_empty_items():
    """render_buffer should ignore empty or falsy items."""
    out = render_buffer(["", None, "hello", ""], indent_width=2)
    assert out == "hello"


def test_render_explicit_indent():
    """Explicit Indentation(+1) should increase indentation for subsequent lines."""
    content = [
        "root",
        Indentation(+1),
        "child",
        Indentation(+1),
        "grandchild",
    ]
    out = render_buffer(content, indent_width=2)
    assert out == "root\n  child\n    grandchild"


def test_render_explicit_dedent():
    """Explicit Indentation(-1) should decrease indentation for subsequent lines."""
    content = [
        "root",
        Indentation(+1),
        "child",
        Indentation(-1),
        "sibling",
    ]
    out = render_buffer(content, indent_width=2)
    assert out == "root\n  child\nsibling"


# -------------------------
# implicit indentation tests
# -------------------------

def test_implicit_indent_from_last_line():
    """
    Indentation should be preserved and inferred from the last emitted line.

    The key rule: by default, indentation is relative to the earlier line ('same')
    """
    last_line = "  grandchild"
    last_indentation_level = infer_indent_level(last_line, indent_width=2)
    assert last_indentation_level == 1, f"Incorrect indentation level: {last_indentation_level} (expected: 2)"
    content = [
        "root:",
        "  child:",
        last_line,
    ]
    out = render_buffer(content, indent_width=2)
    print("Buffer rendered:")
    print(out)
    print("----")
    expected = "root:\n  child:\n    grandchild"
    print("Buffer expected:")
    print(expected)
    print("----")
    assert out == expected



def test_implicit_indent_after_multiline_block():
    """
    Indentation inference should work after multiline blocks.
    The next line should follow the indentation of the last line.
    """
    content = [
        "root:",
        "  line1\n    line2\n      line3",
        "next",
    ]
    out = render_buffer(content, indent_width=2)
    assert out == "root:\n  line1\n    line2\n      line3\n      next"



# -------------------------
# shift-signal tests (". ")
# -------------------------

def test_shift_signal_replaced_with_spaces():
    """.<space> prefix should be replaced with spaces before indentation."""
    content = [
        Indentation(+1),
        ". hello",
    ]
    out = render_buffer(content, indent_width=2)
    # ". " → "  ", then indent_level=1 → 2 spaces → total 4 spaces
    assert out == "    hello"


def test_shift_signal_only_on_first_line():
    """Shift-signal should apply only to the first line of a multiline string."""
    content = [
        Indentation(+1),
        ". line1\nline2",
    ]
    out = render_buffer(content, indent_width=2)
    assert out == "    line1\n  line2"


# -------------------------
# mixed behavior tests
# -------------------------

def test_implicit_indent_after_multiline_block():
    """
    Indentation inference should work after multiline blocks.
    The next line should follow the indentation of the last line.
    """
    content = [
        "root:",
        "  line1\n    line2\n      line3",
        "next",
    ]
    out = render_buffer(content, indent_width=2)
    assert out == "root:\n  line1\n    line2\n      line3\n      next"



def test_multiline_emit_with_explicit_indent():
    """Multiline strings should be indented consistently and infer indentation from the last line."""
    content = [
        Indentation(+1),
        "line1\nline2\n  line3",
    ]
    out = render_buffer(content, indent_width=2)
    assert out == "  line1\n  line2\n    line3"
