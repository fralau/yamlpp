"""
Test the interpreter (basic functions)
"""
from pathlib import Path

from super_collections import SuperDict


from yamlpp import Interpreter
from yamlpp.util import print_yaml

CURRENT_DIR = Path(__file__).parent 




SOURCE_DIR = CURRENT_DIR / 'source'

def test_01():
    """
    Test first YAMLpp program ever (static)
    """
    FILENAME = SOURCE_DIR / 'test1.yaml'
    i = Interpreter()
    i.load(FILENAME)
    assert i.context is not None, "Context should not be empty"


    tree = i.tree
    r = i.yaml # renders
    print_yaml(r)

    # interpretation
    assert tree.server.host == 'localhost'

    # .switch
    assert tree.server.url == 'http://test.example.com'

    # .foreach: check we have the same users and they have the same roles
    users = i.context['users'] # from the source
    assert [account.name for account in tree.accounts] == users
    assert [account.role for account in tree.accounts] == ['user'] * len(users)
    
    # .if
    assert tree.features.debug == False


def test_02():
    "Test YAMLpp with modifications"
    FILENAME = SOURCE_DIR / 'test1.yaml'
    i = Interpreter()
    i.load(FILENAME, render=False) # suspend rendering

    assert i.context is not None, "Context should not be empty"
    i.context.env = 'dev'
    i.context.comment = 'This is added'

    tree = i.tree
    r = i.yaml # renders
    print_yaml(r)
    
    # .switch
    assert tree.server.url == 'http://localhost:5000'
    
    # .if
    assert tree.features.debug == True


def test_import_01():
    "Test of import"
    FILENAME = SOURCE_DIR / 'test2.yaml'
    i = Interpreter()
    i.load(FILENAME)

    tree = i.tree
    r = i.yaml # renders
    print_yaml(r)

    # .switch
    assert tree.server.url == 'http://test.example.com'
    
    # .if
    assert tree.features.debug == False   

    # imported
    # --------
    assert tree.database.engine == 'postgresql'


    # this one involves an interpretation
    assert tree.logging.file == 'logs/test/app.log'

    # .if based on global
    assert tree.database.port == 5434
    assert tree.database.name == "demo_db"

    # test that the local parameter in imported yamlpp {{ host } overrides the global one
    assert tree.database.host == 'my_host.local'
    assert tree.security.allowed_hosts == ['my_host.local', '127.0.0.1']

def test_import_02():
    "Test of import"
    FILENAME = SOURCE_DIR / 'test2.yaml'
    i = Interpreter()
    i.load(FILENAME, render=False)
    # modify parameter before rendering
    i.context.env = 'prod'

    tree = i.tree
    r = i.yaml # renders
    print_yaml(r)

    # .if based on global
    assert tree.database.port == 5432, "Error in .if"
    assert tree.database.name == "prod_db", "Error in .if"


def test_module():
    "Testing the .module instruction"
    FILENAME = SOURCE_DIR / 'test_module.yaml'
    i = Interpreter()
    i.load(FILENAME)

    tree = i.tree
    r = i.yaml # renders
    print_yaml(r)

    data = tree.data
    assert data.greeting == "Hello Hello world!", "Error in module function"
    assert data.shout == "JOE!!!", "Error in module filter"
    assert data.app_name == "YAMLpp", "Error in module variable"


def test_function():
    "Testing a function"
    FILENAME = SOURCE_DIR / 'test_function.yaml'
    i = Interpreter()
    i.load(FILENAME)
    tree = i.tree
    r = i.yaml # renders
    print_yaml(r)


def test_rendered_keys():
    "Minimal test for foreach with rendered keys"

    yaml_source = """
.context:
  users:
    - { id: 1, name: joe, role: admin }
    - { id: 2, name: jill, role: user }

accounts:
  .foreach:
    .values: [u, "{{ users }}"]
    .do:
      "{{ u.name }}":
            id: "{{ u.id }}"
            role: "{{ u.role }}"
"""

    i = Interpreter()
    i.load_text(yaml_source)

    data = i.tree

    print_yaml(i.yaml)

    #Expected keys
    assert list(data.accounts.keys()) == ["joe", "jill"]

    # Check values
    assert data.accounts.joe.id == 1
    assert data.accounts.joe.role == "admin"

    assert data.accounts.jill.id == 2
    assert data.accounts.jill.role == "user"
