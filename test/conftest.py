"""
Configuration of tests for Pytest
"""
import pytest
from rich.console import Console
from rich.text import Text

console = Console()



def pytest_runtest_logstart(nodeid, location):
    """
    Called when pytest starts running a test.
    nodeid: "path::test_function"
    location: (path, lineno, testname)
    """
    path, lineno, testname = location
    msg = Text(f"▶ {testname} (line:{lineno})", style="green")
    print()
    console.print(msg)