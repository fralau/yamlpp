"""
Tests of the .eval construct
"""

from protein.test import protein_comp, print_yaml

def test_eval_string():
    "Test a normal string (nothing special)"

    p = """
    msg:
      .eval: "hello"
    """
    _yaml, tree = protein_comp(p)
    assert tree.msg == "hello"


def test_eval_expression():
    "Eval expression (normal)"

    p = """
    v:
      .eval: "{{ 2 * 2}}"
    """
    _yaml, tree = protein_comp(p)
    assert tree.v == 4


def test_eval_quoted():
    "Eval a quoted expression"

    p = """
    v:
      .eval: "#!literal{{ 2 * 2 }}"
    """
    yaml, tree = protein_comp(p)
    print_yaml(yaml)
    assert tree.v == 4



def test_eval_quoted_list():
    "Eval a quoted expression that returns a list"
    p = """
    l:
      .eval: "#!literal {{ [2, 4, 5] }}"
    """
    yaml, tree = protein_comp(p)
    print_yaml(yaml)
    assert tree.l == [2, 4, 5]