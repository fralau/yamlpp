"""
Test the client's behavior

With round-trips.
"""

import subprocess
import sys
import tempfile
import pathlib
import ast


import pytest
import json
import tomlkit

CLI = ["yamlpp", '-d']

PERSONS = ['Joe', 'Annie', 'Hamilton']

JSON_FILE = f"""
server:
    foo: bar
    baz: 5
    users: [{', '.join(PERSONS)}]
"""

def snip(s:str, length:str=20):
    """
    Short a string
    """
    if len(s) > length:
        return f"...{s[-20:]}"
    else:
        return s

def run_cli(args, input_file=None):
    """Run the yamlpp CLI with given arguments and optional input file.
    
    Returns a CompletedProcess object. If the command fails (non‑zero return code),
    stderr and stdout are included in the AssertionError message for easier debugging.
    """
    cmd = CLI + args
    if input_file:
        cmd.append(str(input_file))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Running: {[snip(item) for item in cmd]}")
    print("Result:\n[---\n", result.stdout)
    print("---]")
    assert result.stdout + result.stderr, f"Both stdout and stderr are empty: {cmd}"
    if result.returncode != 0:
        raise AssertionError(
            f"yamlpp failed:\n"
            f"  command: {' '.join(cmd)}\n"
            f"  returncode: {result.returncode}\n"
            f"  stdout:\n{result.stdout}\n"
            f"  stderr:\n{result.stderr}"
        )
    return result


def make_temp_yaml(content: str):
    """Create a temporary YAML file containing the provided content."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
    tmp.write(content.encode("utf-8"))
    tmp.flush()
    assert pathlib.Path(tmp.name).is_file(), f"Failed to create {tmp.name}!"
    return pathlib.Path(tmp.name)

def check_round_trip(tree):
    """
    Check that the tree is round-trip
    """
    server = tree['server']
    assert isinstance(server, dict), f"Failed to serialize map into a dict (returned a {type(server).__name__})"
    assert server['foo'] == 'bar', "Failed to serialize map "
    assert server['baz'] == 5, "Failed to serialize int (instead of string) "
    users = server['users']
    assert isinstance(users, list), f"Failed to serialize sub-sequence into a list (returned a {type(users).__name__})"
    assert users == PERSONS, "Failed to serialize sub-sequence "

# ---------------------------
# Basic tests
# ---------------------------

def test_help_message():
    """Verify that the CLI help message displays usage and options correctly."""
    result = run_cli(["-h"])
    assert result.returncode == 0
    assert "YAML Preprocessor" in result.stdout
    assert "--set KEY=VALUE" in result.stdout

def test_basic_rendering(tmp_path):
    """Check that a simple YAML file is rendered correctly in default format."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(JSON_FILE)
    result = run_cli(["-f", "yaml"], yaml_file)
    assert result.returncode == 0
    assert "foo: bar" in result.stdout

def test_set_variable(tmp_path):
    """Ensure that variables passed via --set are substituted in the YAML output."""
    yaml_file = tmp_path / "config.yaml"
    my_var = 42
    yaml_file.write_text(f"value: { my_var }\n")
    result = run_cli(["--set", f"myvar= { my_var }", "-f", "yaml"], yaml_file)
    assert result.returncode == 0
    assert f"value: { my_var }" in result.stdout

def test_output_to_file(tmp_path):
    """Confirm that the -o option writes rendered output to a file."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(JSON_FILE)
    out_file = tmp_path / "out.yaml"
    result = run_cli(["-o", str(out_file)], yaml_file)
    print("Screen output:", result.stderr)
    assert result.returncode == 0
    assert out_file.exists(), f"Cannot find YAML output file: {snip(out_file.name)}"
    assert "foo: bar" in out_file.read_text()


def test_initial_flag(tmp_path):
    """Verify that the -i flag shows the original YAML before processing."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(JSON_FILE)
    result = run_cli(["-i"], yaml_file)
    assert result.returncode == 0
    assert "foo: bar" in result.stderr

# ---------------------------
# Test other formats
# ---------------------------
def test_json_output(tmp_path):
    """Check that YAML input is correctly rendered as JSON when using -f json."""
    yaml_file = tmp_path / "config.yaml"

    yaml_file.write_text(JSON_FILE)
    result = run_cli(["-f", "json"], yaml_file)
    assert result.returncode == 0
    # check that it's valid json:
    tree = json.loads(result.stdout)
    check_round_trip(tree)

def test_toml_output(tmp_path):
    """Check that YAML input is correctly rendered as TOML when using -f toml."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(JSON_FILE)
    result = run_cli(["-f", "toml"], yaml_file)
    assert result.returncode == 0
    # TOML output should look like key = "value"
    tree = tomlkit.loads(result.stdout)
    check_round_trip(tree)

def test_python_output(tmp_path):
    """Check that YAML input is correctly rendered as Python dict when using -f python."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(JSON_FILE)
    result = run_cli(["-f", "python"], yaml_file)
    print(result.stdout, "\n")
    assert result.returncode == 0
    try:
        tree = ast.literal_eval(result.stdout)
    except ValueError as e:
        raise ValueError(f"Cannot read Python expr: {e} \n{result.stdout}")
    check_round_trip(tree)

