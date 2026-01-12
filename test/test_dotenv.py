"Higher level tests on dotenv"

from string import Template
from pathlib import Path
from protein import Interpreter
from protein.util import print_yaml


CONFIG_FILENAME = 'test.env'
CONFIG = """
# This is a comment
foo=5
bar="A string"
"""

INSTRUCTION = Template("""
# This is a comment
.define:
    .load: $CONFIG_FILENAME
output:
    value: "{{ foo }} - {{ bar }}"
""").substitute(CONFIG_FILENAME=CONFIG_FILENAME)



def test_dotenv_read(tmp_path):
    "Read a dotenv file"
    full_filename = Path(tmp_path) / CONFIG_FILENAME
    full_filename.write_text(CONFIG)
    i = Interpreter(source_dir=tmp_path)
    tree = i.load_text(INSTRUCTION)
    print_yaml(i.yamlpp, "Original as loaded")
    print_yaml(i.yaml, "Target")
    assert tree.output.value == "5 - A string"
    