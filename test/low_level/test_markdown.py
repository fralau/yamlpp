"""
Test the reading of markdown files
"""

import pytest
from protein.util import markdown_to_tree, loads_markdown


def test_frontmatter_extraction():
    """
    Front‑matter must be parsed into r["meta"], and the body must remain intact.
    """
    md = """---
title: Hello
tags: [a, b]
---
Body text
"""
    r = loads_markdown(md)
    assert r["meta"] == {"title": "Hello", "tags": ["a", "b"]}
    assert r["text"] == "Body text"


def test_frontmatter_filename():
    """
    The filename argument must be preserved in the returned dictionary.
    """
    md = """---
a: 1
---
X
"""
    r = loads_markdown(md, filename="test.md")
    assert r["filename"] == "test.md"


def test_unstructured_mode_returns_raw_text():
    """
    structured=False must return the raw Markdown body as a string.
    """
    md = """# Title
Body"""
    r = loads_markdown(md, structured=False)
    assert r["text"] == "# Title\nBody"


def test_structured_mode_returns_tree():
    """
    structured=True must return a list of node dictionaries.
    """
    md = """# Title
Body"""
    r = loads_markdown(md, structured=True)
    assert isinstance(r["text"], list)
    assert r["text"][0]["title"] == "Title"
    assert r["text"][0]["body"] == "Body"


def test_single_heading():
    """
    A single heading must produce a single top‑level node with its body.
    """
    md = """# Title
Body text"""
    tree = markdown_to_tree(md)
    assert tree == [
        {
            "title": "Title",
            "body": "Body text",
        }
    ]


def test_two_sibling_sections():
    """
    Two top‑level headings must produce two sibling nodes.
    """
    md = """# A
Body A
# B
Body B
"""
    tree = markdown_to_tree(md)
    assert tree == [
        {"title": "A", "body": "Body A"},
        {"title": "B", "body": "Body B"},
    ]


def test_nested_sections():
    """
    Nested headings must form a parent node with child nodes under 'nodes'.
    """
    md = """# A
intro
## A.1
text 1
## A.2
text 2
"""
    tree = markdown_to_tree(md)
    assert tree == [
        {
            "title": "A",
            "body": "intro",
            "nodes": [
                {"title": "A.1", "body": "text 1"},
                {"title": "A.2", "body": "text 2"},
            ],
        }
    ]


def test_three_levels():
    """
    Three levels of headings must produce a three‑level nested node structure.
    """
    md = """# A
root
## B
mid
### C
leaf
"""
    tree = markdown_to_tree(md)
    assert tree == [
        {
            "title": "A",
            "body": "root",
            "nodes": [
                {
                    "title": "B",
                    "body": "mid",
                    "nodes": [
                        {"title": "C", "body": "leaf"}
                    ],
                }
            ],
        }
    ]


def test_prune_empty_nodes():
    """
    Nodes without subnodes must not contain an empty 'nodes' list.
    """
    md = """# A
text"""
    tree = markdown_to_tree(md)
    assert "nodes" not in tree[0]


def test_body_no_trailing_newline():
    """
    Body text must not end with a trailing newline after parsing.
    """
    md = """# A
line1
line2
"""
    tree = markdown_to_tree(md)
    assert tree[0]["body"] == "line1\nline2"


def test_empty_body():
    """
    A heading followed immediately by another heading must produce an empty body.
    """
    md = """# A
## B
text"""
    tree = markdown_to_tree(md)
    assert tree[0]["body"] == ""
    assert tree[0]["nodes"][0]["body"] == "text"
