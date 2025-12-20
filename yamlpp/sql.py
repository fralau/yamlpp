"""
Foundation of the SQLAlchemy binding

Not a lot of code, but carefully crafted.
"""

from typing import Any
import subprocess, json

# This module exports sql_create_engine and SQLConnection
from sqlalchemy import create_engine as sql_create_engine, text as sql_text
from sqlalchemy.engine import Connection as SQLConnection
from sqlalchemy.exc import OperationalError as SQLOperationalError




# -------------------------
# General
# -------------------------

ElementaryTable = list[dict[str, Any]]

def sql_query(engine, query) -> ElementaryTable:
    "Make a query on an engine"
    if engine == osquery:
        # OSqueryEngine is a function
        try:
            return osquery(query)
        except Exception as e:
            raise RuntimeError(f"OSQuery Error on engine '{engine}': {e} ")
    else:
        # print("Engine class:", engine.__class__.__module__)
        with engine.begin() as conn:
            # we open with autocommit
            result = conn.execute(sql_text(query))
            if result.returns_rows:
                # it's important to map already at this stage
                # to immediately release the connection object.
                return result.mappings().all()
            else:
                return []

# -------------------------
# osquery engine
# -------------------------



def osquery(query):
    "Query osqueryi and return a JSON table, or fail gracefully."
    try:
        result = subprocess.run(
            ["osqueryi", "--json", query],
            capture_output=True,
            text=True,
            check=True
        )
    except FileNotFoundError:
        # osqueryi is not installed or not in PATH
        raise RuntimeError("osqueryi command not found. Please install osquery.")
    except subprocess.CalledProcessError as e:
        # osqueryi exists but the query failed
        raise RuntimeError(f"osqueryi failed: {e.stderr.strip()}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON returned by osqueryi: {result.stdout!r}")







