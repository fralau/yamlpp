"""
Test the Export functions
"""

import pytest
import json
import tomlkit
import ruamel.yaml
from io import StringIO

# --- import your functions ---
from yamlpp.util import to_yaml, to_toml, to_json, normalize

yaml = ruamel.yaml.YAML()

# -------------------------
# Fixtures: reusable sample trees
# -------------------------
@pytest.fixture
def sample_tree():
    # A simple YAML tree with nested dict and list
    return yaml.load("""
    app:
      name: myservice
      version: 1.0
      features:
        - logging
        - metrics
    """)

@pytest.fixture
def nested_tree():
    # A YAML tree with booleans, lists, and nested dicts
    return yaml.load("""
    database:
      host: localhost
      ports: [5432, 5433]
      enabled: true
    """)

# -------------------------
# Tests for normalize
# -------------------------
def test_normalize_dict(sample_tree):
    # Ensure normalize converts a CommentedMap into a plain dict
    plain = normalize(sample_tree)
    assert isinstance(plain, dict)
    assert plain["app"]["name"] == "myservice"
    assert plain["app"]["features"] == ["logging", "metrics"]

def test_normalize_list():
    # Ensure normalize converts a CommentedSeq into a plain list
    data = yaml.load("[1, 2, 3]")
    plain = normalize(data)
    assert plain == [1, 2, 3]

def test_normalize_scalar():
    # Ensure scalars (like integers) are returned unchanged
    data = yaml.load("42")
    plain = normalize(data)
    assert plain == 42

# -------------------------
# Tests for to_yaml
# -------------------------
def test_to_yaml_roundtrip(sample_tree):
    # Dump to YAML string and reload: should preserve structure and values
    yaml_str = to_yaml(sample_tree)
    reloaded = yaml.load(yaml_str)
    assert reloaded["app"]["name"] == "myservice"
    assert reloaded["app"]["version"] == 1.0

def test_to_yaml_preserves_lists(nested_tree):
    # Ensure lists are serialized correctly in YAML output
    yaml_str = to_yaml(nested_tree)
    assert "ports:" in yaml_str
    assert "- 5432" in yaml_str or "[5432" in yaml_str

# -------------------------
# Tests for to_toml
# -------------------------
def test_to_toml_structure(sample_tree):
    # Convert to TOML and parse back: values should match original
    toml_str = to_toml(sample_tree)
    doc = tomlkit.parse(toml_str)
    assert doc["app"]["name"] == "myservice"
    assert doc["app"]["features"][0] == "logging"

def test_to_toml_nested(nested_tree):
    # Nested dicts and lists should serialize correctly to TOML
    toml_str = to_toml(nested_tree)
    doc = tomlkit.parse(toml_str)
    assert doc["database"]["enabled"] is True
    assert doc["database"]["ports"][1] == 5433

# -------------------------
# Tests for to_json
# -------------------------
def test_to_json_structure(sample_tree):
    # Convert to JSON and parse back: values should match original
    json_str = to_json(sample_tree)
    obj = json.loads(json_str)
    assert obj["app"]["version"] == 1.0
    assert obj["app"]["features"] == ["logging", "metrics"]

def test_to_json_nested(nested_tree):
    # Nested dicts and lists should serialize correctly to JSON
    json_str = to_json(nested_tree)
    obj = json.loads(json_str)
    assert obj["database"]["host"] == "localhost"
    assert obj["database"]["ports"] == [5432, 5433]
    assert obj["database"]["enabled"] is True
