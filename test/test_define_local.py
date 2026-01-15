from protein.test import protein_comp

def test_define_incrementally_builds_frame():
    """
    .define builds a frame incrementally.
    """
    src = """
    .define:
      a: 10
      b: "{{ a * 2 }}"
    .b:
    """
    _yaml, tree = protein_comp(src)
    assert tree.b == 20
    assert tree.b != 'foo' # sentinel check

def test_local_creates_new_frame():
    """
    .local creates a new frame and its bindings do not escape.
    """
    src = """
    .local:
      x: 1
      y: 2
    .x:
    .y:
    """
    _yaml, tree = protein_comp(src)
    assert tree.x == 1 
    assert tree.y == 2




def test_local_sees_outer_bindings():
    """
    .local sees bindings defined in the outer frame.
    """
    src = """
    .define:
      a: 10

    .local:
      x: "{{ a }}"
    
    a: "{{ a }}"
    """
    _yaml, tree = protein_comp(src)
    assert tree.a == 10


def test_local_sees_earlier_siblings():
    """
    An expression can see .local values within the same mapping.
    """
    src = """
    .do:
      - .define:
         a: 10
      - .local:
          x: "{{ a }}"
        result: "{{ x }}"
    """
    _yaml, tree = protein_comp(src)
    # assert tree.a == 10
    assert tree.result == 10


def test_local_does_not_see_later_siblings():
    """
    An expression in .local does not see siblings defined after it.
    """
    src = """
    .define: 
        a: 0
    result:
        .local:
            x: "{{ a or 5 }}"
            a: 10
        .x:
    .a:    
    """
    _yaml, tree = protein_comp(src)
    assert tree.result.x == 5
    assert tree.a == 0


def test_local_computes_using_siblings():
    """
    .local can compute derived values using earlier siblings.
    """
    src = """
    .define:
      base: 5
    .base:
    result:
        .local:
          doubled: "{{ base * 2 }}"
        .doubled:
    """
    _yaml, tree = protein_comp(src)
    assert tree.base == 5
    assert tree.result.doubled == 10


def test_local_shadowing_does_not_escape():
    """
    Shadowing inside .local does not affect the outer frame.
    """
    src = """
    .define:
      x: 1
    .x:
    result:
      .local:
        x: 99
        y: "{{ x }}"
      .x:
      .y:
    after: "{{ x }}"
    """
    _yaml, tree = protein_comp(src)
    assert tree.x == 1
    assert tree.result.x == 99
    assert tree.result.y == 99
    assert tree.after == 1


def test_nested_local_inherits_chain():
    """
    Nested .local frames inherit from outer, and siblings locals.
    """
    src = """
    .define:
      a: 1
    .a:
    .local:
        b: 2
    result:
        .local:
          c: "{{ a + b }}"
        .c:
"""
    _yaml, tree = protein_comp(src)
    assert tree.a == 1
    assert tree.result.c == 3


def test_local_returns_final_mapping():
    """
    .local does not return anything; it is necessary to extract values explicitly.
    """
    src = """
    result:
      .local:
        a: 1
        b: 2
        sum: "{{ a + b }}"
      .a:
      .b:
      .sum:
"""
    _yaml, tree = protein_comp(src)
    assert tree.result.a == 1
    assert tree.result.b == 2
    assert tree.result.sum == 3


def test_local_does_not_affect_siblings():
    """
    .local inside a mapping does not affect outer bindings.
    """
    src = """
    .define:
      x: 1
    .x:
    one:
      .local:
        x: 2
        y: "{{ x }}"
      .x:
      .y:
    two: "{{ x }}"
    """
    _yaml, tree = protein_comp(src)
    assert tree.x == 1
    assert tree.one.x == 2
    assert tree.one.y == 2
    assert tree.two == 1


def test_local_sees_all_earlier_keys_in_mapping():
    """
    .local inside a mapping sees all earlier keys in that mapping.
    """
    src = """
    .define:
      a: 1
      b: 2
    
    .a:
    .b:

    result:
      .local:
          sum: "{{ a + b }}"
      .sum:    
    """
    _yaml, tree = protein_comp(src)
    assert tree.a == 1
    assert tree.b == 2
    assert tree.result.sum == 3
