import pytest
from protein import protein_comp
from protein.util import print_yaml
from protein.error import YAMLppError


def test_basic_add_function():
    """
    Ensure that a simple `.function` returning a scalar mapping
    evaluates correctly across multiple `.call` invocations.

    Invocations are by position or by value
    """
    yaml_text = """
test:
  .do:
    - .function:
        .name: add
        .args: [a, b]
        .do:
          value: "{{ a + b }}"

    - .call:
        .name: add
        .args: [3, 4]

    - .call:
        .name: add
        .args: [3, 5]

    - .call: # by name
        .name: add
        .args: 
            a: 5
            b: 4

    - .call:
        .name: add
        .args: 
            a: 5
            b: 5
    - .call: # also in different order
        .name: add
        .args: 
            b: 5
            a: 6
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    assert result.test[0].value == 7
    assert result.test[1].value == 8
    assert result.test[2].value == 9
    assert result.test[3].value == 10
    assert result.test[4].value == 11


def test_basic_add_function_with_variables():
    """
    Ensure that a simple `.function` returning an addition
    evaluates correctly across multiple `.call` invocations
    (with variables).

    Arguments can also evaluate to sequences or mappings.

    Invocations are by position or by value
    """
    yaml_text = """
test:
  .do:
    - .function:
        .name: add
        .args: [a, b] # positional arguments (formal)
        .do:
          value: "{{ a + b }}"


    - .define:
        x: 7
        y: 8
    - .call: # using scalar variables (arguments by mapping)
        .name: add
        .args: 
            a: "{{ x }}"
            b: "{{ y }}" 
    - .call: # using scalar variables (arguments by sequence)
        .name: add
        .args: ["{{ x }}", "{{ y }}"]

    - .define:
        x: [1, 2, 3]
        y: [4, 5, 6]
    - .call: # using sequence list arguments (concatenation)
        .name: add
        .args: 
            a: "{{ x }}"
            b: "{{ y }}" 
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    assert result.test[0].value == 15
    assert result.test[1].value == 15
    assert result.test[2].value == [1, 2, 3, 4, 5, 6]


def test_mapping_return_function():
    """
    Ensure that a `.function` returning a mapping produces the expected
    structure for different argument values.
    """
    yaml_text = """
test:
  .do:
    - .function:
        .name: create
        .args: [env, max_retries]
        .do:
          environment:
            name: "{{ env }}_{{ max_retries }}"
            path: "path/{{env}}"
            filename: "{{env}}.py"
            max_retries: "{{ max_retries }}"

    - .call:
        .name: create
        .args: ['test', 5]

    - .call:
        .name: create
        .args: ['test', 3]

    - .call:
        .name: create
        .args:
            env: prod
            max_retries: 3
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    env1 = result.test[0].environment
    env2 = result.test[1].environment
    env3 = result.test[2].environment

    assert env1.name == "test_5"
    assert env1.path == "path/test"
    assert env1.filename == "test.py"
    assert env1.max_retries == 5

    assert env2.name == "test_3"
    assert env2.path == "path/test"
    assert env2.filename == "test.py"
    assert env2.max_retries == 3

    assert env3.name == "prod_3"
    assert env3.path == "path/prod"
    assert env3.filename == "prod.py"
    assert env3.max_retries == 3


def test_closure_captures_definition_environment():
    """
    Ensure that a `.function` captures the dynamic environment at
    definition time, even if the environment changes later.

    This confirms the principle of late binding.
    """
    yaml_text = """
test:
  .local:
        x: 10
  .do:

    - .function:
        .name: get_x
        .args: []
        .do:
          value: "{{ x }}"

    - .define:
        x: 999

    - .call:
        .name: get_x
        .args: []
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    assert result.test.value == 10


def test_arguments_override_captured_environment():
    """
    Ensure that `.call` arguments override captured names inside
    the closure environment.
    """
    yaml_text = """
test:
  .local:
    x: 5
  .do:
    - .function:
        .name: f
        .args: [x]
        .do:
          value: "{{ x }}"

    - .call:
        .name: f
        .args: [42]
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    assert result.test.value == 42


def test_static_closure_on_mutable():
    """
    Ensure that closure capture is static: 
    even if the captured environment contains a mutable object,
    mutations to that object are NOT visible.

    Even though `data.items` is a list (mutable), then changing its contents
    after the function is defined doea not affects what the closure sees.
    """
    yaml_text = """
test:
  .local:
        data:
          foos: [1, 2]

  .do:
    - .function:
        .name: read_foos
        .args: []
        .do:
          value: "{{ data.foos }}"

    # Mutate the mutable object AFTER the function is created
    - .define:
        data:
          foos: [1, 2, 3]

    - .print: "Data items are {{ data.foos }}"

    - .call:
        .name: read_foos
        .args: []
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    # Even though the function captured a reference to the mutable list,
    # and the list was mutated, the closure still sees the original list contents.
    assert result.test.value == [1, 2]

def test_static_closure_on_immutable():
    """ 
    Ensure that closure capture is static.
    
    Changing the value of `data.counter` has no effect on the closure,
    which still references the old int value.
    """
    yaml_text = """
test:
  .local:
        data:
          counter: 1
  .do:
    - .function:
        .name: read_counter
        .args: []
        .do:
          value: "{{ data.counter }}"

    - .define:
        data:
          counter: 2

    - .print: "Data counter is {{ data.counter }}"

    - .call:
        .name: read_counter
        .args: []
"""
    yaml, result = protein_comp(yaml_text)
    print_yaml(yaml, "Evaluation")

    assert result.test.value == 1





def test_nested_function_invisible():
    """
    YAMLpp `.function` is declarative and its declarations belong to the
    lexical scope in which they appear. A nested `.function` inside another
    function is therefore declared *inside that function’s lexical scope* and
    is not visible from the outside unless explicitly exported.

    In this model:
    - `.function` does not execute its `.do` block at definition time.
    - Nested function declarations (e.g. `inner`) are registered in the
      lexical scope of the enclosing function (e.g. `outer`).
    - That lexical scope only becomes active when the enclosing function is
      *called*, because `.call` is what pushes a runtime frame.
    - If the enclosing function is never called, its internal declarations
      never become visible in any runtime frame.
    - Consequently, attempting to `.call inner` from outside `outer` cannot
      succeed, because `inner` is not defined in the outer lexical environment.
    """

    yaml_text = """
test:
  .do:
    - .local:
        x: 1

    - .function:
        .name: outer
        .args: []
        .do:
            .function:
              .name: inner
              .args: []
              .do:
                value: "{{ x }}"

    - .define:
        x: 999

    - .call:
        .name: inner
        .args: []
"""

    with pytest.raises(YAMLppError) as e:
        yaml, result = protein_comp(yaml_text)
    print("Error:", e.value)
    assert "'inner' not found" in str(e.value)



def test_call_undefined_function():
    """
    Ensure that calling an undefined function raises an exception.
    """
    yaml_text = """
test:
  .do:
    - .call:
        .name: does_not_exist
        .args: [1, 2]
"""
    with pytest.raises(Exception):
        protein_comp(yaml_text)


def test_wrong_argument_count():
    """
    Ensure that calling a function with the wrong number of arguments
    raises an error.
    """
    yaml_text = """
test:
  .do:
    - .function:
        .name: add
        .args: [a, b]
        .do:
          value: "{{ a + b }}"

    - .call:
        .name: add
        .args: [1]
"""
    with pytest.raises(YAMLppError):
        protein_comp(yaml_text)


def test_arguments_not_list():
    """
    Ensure that `.args` must be a list and that providing any other
    type raises a TypeError.
    """
    yaml_text = """
test:
  .do:
    - .function:
        .name: add
        .args: [a, b]
        .do:
          value: "{{ a + b }}"

    - .call:
        .name: add
        .args: 123
"""
    with pytest.raises(YAMLppError):
        protein_comp(yaml_text)
