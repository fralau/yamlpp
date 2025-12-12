"""
Integration tests for the !insert directive handled by Interpreter.handle_insert.

These tests:
- use the real Interpreter from yamlpp
- create real temporary files
- verify correct deserialization
- verify .format override
- verify .args passing
- verify YAMLppError on missing files
"""

import pytest
from pathlib import Path

from yamlpp import Interpreter
from yamlpp.error import YAMLppError, Error
from yamlpp.util import to_yaml

def test_insert_basic_yaml(tmp_path):
    """
    Test that !insert loads an external YAML file and returns its parsed content.
    """
    # External file to be inserted
    DATA = {"a": 1, "b": 2}
    TEXT = to_yaml(DATA)
    external = tmp_path / "data.yaml"
    external.write_text(TEXT)

    print(TEXT)
    print("Filename:", external.name)

    # Main YAML using !insert
    main = tmp_path / "main.yaml"
    main.write_text(f"""
root:
  .insert:
    .filename: "{external.name}"
""")



    interp = Interpreter(source_dir=tmp_path)
    interp.load(main)
    result = interp.tree
    print("Result:\n", result)

    assert result["root"] == DATA


def test_insert_missing_file_raises(tmp_path):
    INSERTED = "missing.yaml"
    FULL_INSERTED = tmp_path / INSERTED

    main = tmp_path / 'main.yaml'
    main.write_text(f"""
root:
  .insert:
    .filename: {INSERTED}
""")

    interp = Interpreter(source_dir=tmp_path)

    try:
        # load the main program
        interp.load(main)
        interp.tree
    except YAMLppError as err:
        # This is the case we expect
        assert err.err_type == Error.FILE
        assert INSERTED in str(err)
    except Exception as unexpected:
        # Surface *real* unexpected exceptions directly
        raise AssertionError(
            f"Unexpected exception type: {type(unexpected).__name__}"
        ) from unexpected
    else:
        file_exists = Path(FULL_INSERTED).is_file()
        if file_exists:
            raise AssertionError(f"YAMLppError was not raised because file exists (filename: {FULL_INSERTED})")
        else:
            raise AssertionError(f"YAMLppError was not raised and file does not exist (filename: {FULL_INSERTED})")



def test_insert_with_format_override(tmp_path):
    """
    Test that .format forces a specific deserialization format.
    Here we store JSON in a .txt file and force format=json.
    """
    external = tmp_path / "data.txt"
    external.write_text('{"x": 10, "y": 20}')

    main = tmp_path / "main.yaml"
    main.write_text(f"""
root:
  .insert:
    .filename: "{external.name}"
    .format: "json"
""")

    interp = Interpreter(source_dir=tmp_path, filename=main)
    result = interp.tree

    assert result["root"] == {"x": 10, "y": 20}


def test_insert_with_args(tmp_path):
    """
    Test that .args is passed to the deserializer.
    We use YAML but force 'Loader=SafeLoader' as an example argument.
    """
    external = tmp_path / "data.yaml"
    external.write_text("value: 42\n")

    main = tmp_path / "main.yaml"
    main.write_text(f"""
root:
  .insert:
    .filename: "{external.name}"
    .args:
      Loader: "SafeLoader"
""")

    interp = Interpreter(source_dir=tmp_path)
    interp.load(main)
    result = interp.tree
    assert result["root"] == {"value": 42}
