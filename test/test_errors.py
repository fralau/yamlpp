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

def test_err_content():
    """
    Test YAMLpp program with errors

    Check the content of the error message, including the source filename
    """
    SOURCE_FILE = 'test1.yaml'
    FILENAME = SOURCE_DIR / SOURCE_FILE
    i = Interpreter()
    i.load(FILENAME, render=False) # do not render (modification)
    
    # rename key
    switch = i.initial_tree.server['.switch']
    switch['.cases2'] = switch.pop('.cases')

    

    with pytest.raises(YAMLppError) as e:
        i.render_tree()
    msg = str(e.value)
    print("ERROR:", msg)
    err_msg_content = ["not contain "
                       "'.cases'", 
                       "Line 10", 
                       FILENAME]
    for s in err_msg_content:
        assert str(s) in msg, f"{s} not found in error message: {msg}"

def test_err_duplicate_key():
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