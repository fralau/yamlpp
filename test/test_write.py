"""
Test the write construct
(for producing export files)
"""
from pathlib import Path
from protein import protein_comp
from protein.test import interp, read_file




def test_save_simple(tmp_path):
    "Simple test of .save"

    EXPORT_FILENAME = 'test.txt'

    program = interp("""
.write:
    .filename: $EXPORT_FILENAME
    .text: |
        Hello World
""")
    protein_comp(program, tmp_path)
    out_file = Path(tmp_path) / EXPORT_FILENAME
    result = read_file(out_file)
    assert "Hello World" in result
    assert "foo" not in result


def test_save_with_template(tmp_path):
    "Simple test of .save with template"

    EXPORT_FILENAME = 'test.txt'
    NAME = "Joe Bloggs"

    program = interp("""
.define:
    name: $NAME
.write:
    .filename: $EXPORT_FILENAME
    .text: |
        Hello {{ name }}
""")
    protein_comp(program, tmp_path)
    out_file = Path(tmp_path) / EXPORT_FILENAME
    result = read_file(out_file)
    assert f"Hello {NAME}" in result
    assert "foo" not in result