"""
Test errors of the interpreter (basic functions)
"""
import io
from pathlib import Path

import pytest


from yamlpp import Interpreter
from yamlpp.error import YAMLppError, YAMLValidationError
from yamlpp.util import print_yaml, load_yaml

CURRENT_DIR = Path(__file__).parent 

SOURCE_DIR = CURRENT_DIR / 'source'

def test_err_0():
    """
    Test YAMLpp program with errors
    """
    FILENAME = SOURCE_DIR / 'test1.yaml'
    i = Interpreter()
    i.load(FILENAME, render=False) # do not render (modification)
    
    # rename key
    switch = i.initial_tree.server['.switch']
    switch['.cases2'] = switch.pop('.cases')

    

    with pytest.raises(YAMLppError) as e:
        tree = i.tree
    assert "not contain '.cases'" in str(e.value)
    assert "Line 10" in str(e)

def test_err_1():
    """
    Test a duplicate key
    """
    FIRST_HOST = 'localhost'
    SECOND_HOST = '192.168.1.4'
    source = f"""  
.context:
  env: test
  host: {FIRST_HOST}
  users: [alice, bob, charlie, michael]
  host: {SECOND_HOST}
    """

    # tree = load_yaml(source, is_file=False)

    i = Interpreter()
    with pytest.raises(YAMLValidationError) as e:
        i.load_text(source)
        assert e.err_type == "DuplicateKeyError"