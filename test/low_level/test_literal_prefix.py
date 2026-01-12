"""
Low-level tests for literal prefix handling
(prefix is "#!literal")
"""

from string import Template

import pytest
from protein import Interpreter
from protein.util import LITERAL_PREFIX, strip_prefix

# -------------------------
# strip_prefix tests
# -------------------------

def test_strip_prefix_present():
    s = f"{LITERAL_PREFIX}   Hello world"
    assert strip_prefix(s) == "Hello world"


def test_strip_prefix_absent():
    s = "Hello world"
    assert strip_prefix(s) == "Hello world"


def test_strip_prefix_exact_prefix():
    s = LITERAL_PREFIX
    assert strip_prefix(s) == ""


def test_strip_prefix_non_string():
    assert strip_prefix(123) == 123


# -------------------------
# evaluate_expression tests
# -------------------------

def make_engine():
    p = Interpreter()
    # p.stack = [{}]
    return p


def test_eval_preserves_prefix_in_normal_mode():
    "In normal mode, the literal prefix is preserved"
    p = make_engine()

    # Build the expression safely using Template
    expr = Template("$prefix Hello {{ name }}").substitute(prefix=LITERAL_PREFIX)

    result = p.evaluate_expression(expr, final=False)
    assert result == expr


def test_eval_strips_prefix_in_final_mode():
    "In final mode, the literal prefix is stripped"
    p = make_engine()

    expr = Template("$prefix Hello {{ name }}").substitute(prefix=LITERAL_PREFIX)

    result = p.evaluate_expression(expr, final=True)
    assert result == "Hello {{ name }}"


def test_eval_runs_jinja_when_no_prefix():
    "When there is no literal prefix, Jinja2 is evaluated normally"
    p = make_engine()
    p.stack["name"] = "Laurent"

    expr = "Hello {{ name }}"
    result = p.evaluate_expression(expr)

    assert result == "Hello Laurent"

