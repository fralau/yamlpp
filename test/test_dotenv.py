"Higher level tests on dotenv"


from pathlib import Path
from protein import Interpreter, protein_comp
from protein.test import print_yaml, interp


CONFIG_FILENAME = 'test.env'
CONFIG = """
# This is a comment
foo=5
bar="A string"
"""


def test_dotenv_read(tmp_path):
    "Read a dotenv file"
    INSTRUCTION = interp("""
# This is a comment

.load: $CONFIG_FILENAME

""")
    
    full_filename = Path(tmp_path) / CONFIG_FILENAME
    full_filename.write_text(CONFIG)

    yaml, tree = protein_comp(INSTRUCTION, tmp_path)  
    assert tree.foo == '5'
    assert tree.bar == 'A string'
    print_yaml(yaml, CONFIG_FILENAME)





def test_dotenv_read_with_define(tmp_path):
    "Read a dotenv file and use its values in a .define"
    INSTRUCTION = interp("""
# This is a comment
.define: 
    .load: $CONFIG_FILENAME

output:
    value: "{{ foo }} - {{ bar }}"
""")

    full_filename = Path(tmp_path) / CONFIG_FILENAME
    full_filename.write_text(CONFIG)
    i = Interpreter(source_dir=tmp_path)
    tree = i.load_text(INSTRUCTION)
    
    print_yaml(i.yamlpp, "Original as loaded")
    print_yaml(i.yaml, "Target")
    assert tree.output.value == "5 - A string"
    