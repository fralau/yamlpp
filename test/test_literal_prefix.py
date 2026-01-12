"""
High-level tests for literal prefix handling
(prefix is "#!literal")
"""

import pytest
from protein import Interpreter 
from protein.util import LITERAL_PREFIX

def make_engine():
    p = Interpreter()
    entry = {".name": "buf"}
    p.handle_open_buffer(entry)
    return p


# -------------------------
# handle_write_buffer tests
# -------------------------

def test_write_buffer_strips_literal_prefix():
    "Write a literal-prefixed string into a buffer, output should have prefix stripped"
    p = make_engine()

    entry = {
        ".name": "buf",
        ".text": "#!literal Hello {{ name }}",
        ".indent": 0,
    }

    p.stack["name"] = "Laurent"

    p.handle_write_buffer(entry)

    content = p.stack["buf"]["content"]

    print(content)

    # First element is indentation
    assert content[1] == 0

    # Second element is the stripped text
    assert content[2] == "Hello {{ name }}"


def test_write_buffer_renders_templates_normally():
    "Write a normal string into a buffer, output should have template rendered"
    p = make_engine()

    entry = {
        ".name": "buf",
        ".text": "Hello {{ who }}",
        ".indent": 0,
    }

    p.stack["who"] = "Laurent"

    p.handle_write_buffer(entry)

    content = p.stack["buf"]["content"]

    assert content[2] == "Hello Laurent"



# -------------------------
# Serialization tests
# -------------------------

@pytest.mark.parametrize("fmt", ["yaml", "json", "toml", "python"])
def test_yaml_serialization_strips_literal_prefix(fmt):
    "When serializing to YAML/JSON/TOML, literal prefixes must be stripped"
    p = Interpreter()

    program = """
    .define:
        x: "--ignored--"               # Jinja won't run because of prefix
        value: "$prefix Hello {{ x }}" # This is what will be serialized

    result:
        .value: "{{ value }}"
    """.replace("$prefix", LITERAL_PREFIX)

    p.load_text(program)

    # Serialize the entire state
    output = p.dumps(fmt)
    print(f"Serialized output in {fmt}:\n", output)

    # Prefix must NOT appear in the output
    assert LITERAL_PREFIX not in output

    # The stripped value must appear exactly
    assert "Hello {{ x }}" in output

