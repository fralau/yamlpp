"""
High‑level integration tests for .import_module using pytest's tmp_path.

Everything is contained in this single file:
- the module code (as a string)
- writing the module into tmp_path
- running full Protein programs via protein_comp()
- verifying exported callables, variables, and argument passing
"""

import pytest
from protein import protein_comp
from protein.test import interp,print_yaml


MODULE_CODE = '''
from protein import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    @env.export
    def greet(name: str) -> str:
        return f"Hello {name}"

    @env.export
    def add(x, y):
        return x + y

    @env.export
    def scalar():
        return 42

    @env.export
    def seq():
        return [1, 2, 3]

    @env.export
    def mapping():
        return {"a": 1}

    class X:
        pass

    @env.export
    def bad():
        return X()

    env.variables["app_name"] = "Protein"
'''


def write_module(tmp_path):
    """Write sample.py into tmp_path and return its filename."""
    module_path = tmp_path / "sample.py"
    module_path.write_text(MODULE_CODE)
    return "sample.py"


# ------------------------------------------------------------
# Module import
# ------------------------------------------------------------

def test_import_and_greet(tmp_path):
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.greet: ["Laurent"]
""")
    yaml_out, tree = protein_comp(program, working_dir=tmp_path)
    print_yaml(yaml_out, "Result")
    assert tree == "Hello Laurent"


# ------------------------------------------------------------
# Valid return types
# ------------------------------------------------------------

def test_scalar_return(tmp_path):
    "Returns a scalar"
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.scalar: []
""")
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == 42


def test_sequence_return(tmp_path):
    "Returns a sequence"
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.seq: []
""")
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == [1, 2, 3]


def test_mapping_return(tmp_path):
    "Returns a mapping"
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.mapping: []
""")    
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == {"a": 1}


# ------------------------------------------------------------
# Argument passing
# ------------------------------------------------------------

def test_positional_args(tmp_path):
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.add: [2, 3]
""")   
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == 5


def test_keyword_args(tmp_path):
    module_file = write_module(tmp_path)

    program = interp("""    
.import_module: "$module_file"

.add:
  x: 2
  y: 3
""")
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == 5


def test_args_kwargs_form(tmp_path):
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.add:
  .args: [2]
  .kwargs:
    y: 3
""")
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == 5


# ------------------------------------------------------------
# Invalid return types
# ------------------------------------------------------------

def test_invalid_return_type(tmp_path):
    module_file = write_module(tmp_path)

    program = f"""
.import_module: "{module_file}"

.bad: []
"""
    with pytest.raises(Exception):
        protein_comp(program, working_dir=str(tmp_path))


# ------------------------------------------------------------
# Variables
# ------------------------------------------------------------

def test_module_variable(tmp_path):
    "Test accessing a module variable"
    module_file = write_module(tmp_path)

    program = interp("""
.import_module: "$module_file"

.app_name:
""")
    yaml_out, tree = protein_comp(program, working_dir=str(tmp_path))
    assert tree == "Protein"
