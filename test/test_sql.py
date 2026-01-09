"""
End‑to‑end tests for YAMLpp SQL constructs using a `.do` block
to sequence multiple actions in a single YAMLpp program.

This keeps each test simple:
    • one Interpreter()
    • one load_text()
    • one YAMLpp document containing all steps
"""

from string import Template
import subprocess

import pytest
from unittest.mock import Mock, patch
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from ruamel.yaml.comments import CommentedSeq

from yamlpp import Interpreter, yamlpp_comp
from yamlpp.util import print_yaml
from yamlpp.sql import sql_text, sql_create_engine, osquery
from yamlpp.error import YAMLppError

def inspect_db(engine: Engine):
    "Inspect a db and return info"
    insp = inspect(engine)

    info = {
        "tables": insp.get_table_names(),
        "views": insp.get_view_names(),
        "schemas": insp.get_schema_names(),
        "default_schema": insp.default_schema_name,
    }
    return info

# ---------------------------------------------------------------------------
# TEST 1 — .def_sql inside a .do block
# ---------------------------------------------------------------------------

def test_def_sql_creates_engine():
    """
    Verify that .def_sql creates a SQLAlchemy engine and stores it in the stack.
    """

    yaml = """
    .do:
      - .def_sql:
          .name: db
          .url: "sqlite:///:memory:"
    """

    interp = Interpreter()
    interp.load_text(yaml)
    print("Result:")
    print_yaml(interp.yaml)

    assert "db" in interp.stack
    engine = interp.stack["db"]
    assert isinstance(engine, Engine)
    print(inspect_db(engine))


# ---------------------------------------------------------------------------
# TEST 2 — .exec_sql inside a .do block
# ---------------------------------------------------------------------------

def test_exec_sql_creates_table_and_inserts():
    """
    Verify that .exec_sql executes SQL statements on the engine created by .def_sql.
    """

    yaml = """
    .do:
      - .def_sql:
          .name: db
          .url: "sqlite:///:memory:"

      - .exec_sql:
          .engine: db
          .query: |
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT
            );

      - .exec_sql:
          .engine: db
          .query: |
            INSERT INTO users (name) VALUES ('Alice'), ('Bob');
    """

    interp = Interpreter()
    interp.load_text(yaml)

    engine = interp.stack["db"]
    assert engine is not None

    print(inspect_db(engine))

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) AS n FROM users"))
        first = result.fetchone() 
        print("First:", first)
        assert first[0] == 2


# ---------------------------------------------------------------------------
# TEST 3 — .load_sql inside a .do block, bound to a key
# ---------------------------------------------------------------------------

def test_load_sql_returns_commentedseq_of_dicts():
    """
    Verify that .load_sql returns a CommentedSeq of dict rows and that YAMLpp
    binds the result to the key in the YAML document.
    """

    yaml = """
    .do:
      - .def_sql:
          .name: db
          .url: "sqlite:///:memory:"

      - .exec_sql:
          .engine: db
          .query: |
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT
            );

      - .exec_sql:
          .engine: db
          .query: |
            INSERT INTO users (name) VALUES ('Alice'), ('Bob');

      - .load_sql:
            .engine: db
            .query: "SELECT id, name FROM users ORDER BY id"
    """

    interp = Interpreter()
    interp.load_text(yaml)

    seq = interp.tree
    print(seq)
    print_yaml(interp.yaml, "Output")

    assert isinstance(seq, CommentedSeq)
    assert seq == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]


# ---------------------------------------------------------------------------
# TEST 4 — .load_sql as the root value inside .do
# ---------------------------------------------------------------------------

def test_load_sql_as_root_value():
    """
    Verify that .load_sql can be the final action in a .do block and that
    Interpreter.load_text() returns its value.
    """

    yaml = """
    .do:
      - .def_sql:
          .name: db
          .url: "sqlite:///:memory:"

      - .exec_sql:
          .engine: db
          .query: |
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT
            );

      - .exec_sql:
          .engine: db
          .query: |
            INSERT INTO users (name) VALUES ('Alice'), ('Bob');

      - .load_sql:
          .engine: db
          .query: "SELECT id, name FROM users ORDER BY id"
    """

    interp = Interpreter()
    value = interp.load_text(yaml)

    print(value)

    assert isinstance(value, CommentedSeq)
    assert value[0]["name"] == "Alice"


def test_servers_to_config(tmp_path):
    """
    End-to-end semantic test:
    - Create a SQLite database file
    - Populate a 'servers' table
    - YAMLpp loads it via .load_sql with a declared engine
    - .for iterates through rows
    - .do builds a derived config list
    """

    # --- 1. Create a SQLite DB file ---
    db_path = tmp_path / "servers.db"
    engine = sql_create_engine(f"sqlite:///{db_path}")

    with engine.begin() as conn:
        conn.execute(sql_text("""
            CREATE TABLE servers (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ip   TEXT NOT NULL
            )
        """))
        conn.execute(sql_text("""
            INSERT INTO servers (name, ip) VALUES
            ('alpha', '10.0.0.1'),
            ('beta',  '10.0.0.2'),
            ('gamma', '10.0.0.3')
        """))

    # --- 2. YAMLpp program declaring the engine and loading SQL ---
    yaml_program = tmp_path / "program.yaml"

    program = Template("""

.def_sql:
    .name: db
    .url: "sqlite:///$filename"
                       
.local:
    servers:
        .load_sql:
            .engine: db
            .query: "SELECT id, name, ip FROM servers ORDER BY id"

config:
  .foreach: 
    .values: [server, "{{servers}}"]
    .do:
        - name: "{{ server.name }}"
          address: "{{ server.ip }}"
""")
    text = program.substitute(filename=db_path)
    yaml_program.write_text(text)

    # --- 3. Run interpreter ---
    interp = Interpreter(source_dir=tmp_path)
    result = interp.load(yaml_program)
    print_yaml(interp.yaml, filename="Interpreted file")

    # --- 4. Assertions ---
    cfg = result.config

    assert isinstance(cfg, list)
    assert len(cfg) == 3

    assert cfg[0]["name"] == "alpha"
    assert cfg[0]["address"] == "10.0.0.1"

    assert cfg[1]["name"] == "beta"
    assert cfg[1]["address"] == "10.0.0.2"

    assert cfg[2]["name"] == "gamma"
    assert cfg[2]["address"] == "10.0.0.3"


# -------------------------
# osquery engine
# -------------------------

OS_QUERY_PROGRAM = """
time:
    .load_sql:
        .engine: osquery
        .query: "SELECT * FROM TIME"
"""

def test_os_query():
    "Test OS Query"

    # this query, because of the collapse rule (1 row)
    # will return a dictionary
    i = Interpreter()
    tree = i.load_text(OS_QUERY_PROGRAM)
    print_yaml(i.yaml, "osquery")
    # all values from osquery are strings
    from datetime import datetime
    assert tree.time.year  == str(datetime.now().year)
    assert tree.time.month == str(datetime.now().month)


def test_unit_osquery_not_installed():
    "Unit test, not installed"
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="osqueryi command not found"):
            osquery("SELECT 1;")


def test_unit_osquery_query_failure():
    "Query error"
    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["osqueryi"],
        stderr="syntax error"
    )

    with patch("subprocess.run", side_effect=error):
        with pytest.raises(RuntimeError, match="osqueryi failed"):
            osquery("BAD SQL")


def test_osquery_not_installed():
    "osquery not installed (high-level test)"
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(YAMLppError, match="osqueryi command not found"):
            yaml, tree = yamlpp_comp(OS_QUERY_PROGRAM)