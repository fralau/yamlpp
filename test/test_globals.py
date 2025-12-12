"""
Test the globals
"""
import pytest

from yamlpp import Interpreter
from yamlpp.util import print_yaml
from yamlpp.error import YAMLppError

USERNAME = 'db_user'
SERVICE = 'my_server'
PASSWORD = 'secret123'

class DummyKeyring:
    def __init__(self):
        self._store = {}

    def set_password(self, service, username, password):
        """Simulate storing a password."""
        self._store[(service, username)] = password

    def get_password(self, service, username):
        """Simulate retrieving a password."""
        try:
            password = self._store[(service, username)]
        except KeyError:
            raise KeyError(f"Cannot find password for {service}/{username}!")
        print(f"Retrieved password for {service}/{username}: {password}")
        return password
    
keyring = DummyKeyring()
keyring.set_password(SERVICE, USERNAME, PASSWORD)

def test_dummy():
    "Test the dummy keyring"
    assert keyring.get_password(SERVICE, USERNAME) == PASSWORD




def test_keyring():
    "Test the keyring buit-in function"


    yaml = """
.context:
    service: %s
    username: %s

server:
    user: "{{ username }}"
    password: "{{ get_password(service, username)}}" #you are of course not supposed to do that!
""" % (SERVICE, USERNAME)
    
    FUNCTIONS = {'get_password': keyring.get_password}
    # overwrite with our dummy
    i = Interpreter(functions=FUNCTIONS)
    i.load_text(yaml, render=False)
    r = i.yaml
    print_yaml(r)


def test_keyring_error():
    "Test the keyring buit-in function, with error"

    # YAML contains a wrong name
    yaml = """.context:
    service: %s
    username: %s

server:
    user: "{{ username }}"
    password: "{{ get_password(service, username + '2')}}" #you are of course not supposed to do that!
""" % (SERVICE, USERNAME)
    
    FUNCTIONS = {'get_password': keyring.get_password}
    # overwrite with our dummy
    i = Interpreter(functions=FUNCTIONS)
    i.load_text(yaml, render=False) # delay so as to be able to capture the error
    with pytest.raises(YAMLppError) as e:
        i.yaml
    print(e.value)
    assert "Line 5" in str(e.value)
    assert "get_password(" in str(e.value)