"""
Test export
"""
import io
from pathlib import Path

from yamlpp import Interpreter
from yamlpp.error import YAMLppError, YAMLValidationError
from yamlpp.util import print_yaml, load_yaml

CURRENT_DIR = Path(__file__).parent 
EXPORT = "_export" 

SOURCE_DIR = CURRENT_DIR / 'source'

EXPORT_DIR = SOURCE_DIR / EXPORT
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

def test_export_enviroment():
    assert SOURCE_DIR.is_dir()
    assert EXPORT_DIR.is_dir()
    print("Export dir: ", EXPORT_DIR)

def test_export_0():
    """
    Test YAMLpp export
    """
    
    SOURCE_FILENAME = SOURCE_DIR / 'test1.yaml'
    EXPORT_FILENAME = f'{EXPORT}/export1.yaml' # relative



    i = Interpreter()
    i.load(SOURCE_FILENAME)
    
    # Replace the accounts in the source file by an export clause
    accounts = i.initial_tree.pop('accounts')
    block = {'.filename': EXPORT_FILENAME, '.do' : {'accounts': accounts}}
    i.initial_tree['.export'] = block

    # Compile and export
    print_yaml(i.yaml)

    # check
    exported = SOURCE_DIR / EXPORT_FILENAME
    assert exported.is_file()
    i2 = Interpreter()
    i2.load(exported)
    tree = i2.initial_tree
    print_yaml(i2.yamlpp, filename=EXPORT_FILENAME)
    len(tree) == 4
    tree.accounts[1].name = 'bob'
    tree.accounts[2].name = 'charlie'
    # this is pure YAML:
    assert i2.yamlpp == i2.yaml, "YAML produced should be identical to YAMLpp source"
