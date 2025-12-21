"""
Tests for the `.foreach` directive in YAMLpp.
"""

import pytest
from yamlpp import yamlpp_comp
from yamlpp.error import YAMLppError
from yamlpp.util import print_yaml


def test_foreach_basic_list():
    """
    `.foreach` over a simple list should produce a list of results,
    with correct variable binding and no collapsing.
    """
    program = """
    result:
      .foreach:
        .values: [x, [1, 2, 3]]
        .do:
          - "{{x}}"
    """

    yaml, tree = yamlpp_comp(program)
    print_yaml(yaml, "Result")
    assert list(tree.result) == [1, 2, 3]



def test_foreach_basic_singleton():
    """
    `.foreach` over a simple list should produce a list of results,
    with correct variable binding and no collapsing.
    """
    program = """
    result:
      .foreach:
        .values: [x, [1]]
        .do:
          - "{{x}}"
    """

    yaml, tree = yamlpp_comp(program)
    print_yaml(yaml, "Result")
    assert list(tree.result) == [1]


def test_foreach_map():
    """
    `.foreach` collects maps, by default
    """
    program = """
    result:
      .foreach:
        .values: [item, ["a", "b"]]
        .do:
          - "{{item}}": 42
    """

    yaml, tree = yamlpp_comp(program)
    print_yaml(yaml)
    assert tree.result.a == 42 
    assert tree.result.b == 42


def test_foreach_map_no_collect():
    """
    `.foreach` with `.collect_maps` set to false
    """
    program = """
    result:
      .foreach:
        .values: [item, ["a", "b"]]
        .collect_mappings: false
        .do:
          - "{{item}}": 42
    """

    yaml, tree = yamlpp_comp(program)
    print_yaml(yaml)
    assert tree.result[0].a == 42 
    assert tree.result[1].b == 42


