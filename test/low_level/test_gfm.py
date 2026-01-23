"""
Tests for the GitHub‑flavored Markdown (GFM) parser and renderer

See also test_markdown.py for more general Markdown tests.
"""

import pytest
from protein.global_context import make_markdown_parser, to_html


# ------------------------------------------------------------
#  Parser construction invariants
# ------------------------------------------------------------

def test_make_markdown_parser_returns_fresh_instance():
    "Tests the factory"
    md1 = make_markdown_parser()
    md2 = make_markdown_parser()
    assert md1 is not md2
    assert md1.options is not md2.options
    assert md1.block is not md2.block
    assert md1.inline is not md2.inline
    assert md1.core is not md2.core
    assert md1.renderer is not md2.renderer


def test_parser_has_expected_plugins_enabled():
    md = make_markdown_parser()

    # Footnotes plugin registers several renderer rules
    expected = {
        "footnote_ref",
        "footnote_anchor",
        "footnote_open",
        "footnote_close",
        "footnote_block_open",
        "footnote_block_close",
    }

    assert expected.issubset(md.renderer.rules.keys())



def test_parser_has_all_containers_registered():
    md = make_markdown_parser()
    containers = ["note", "tip", "warning", "danger", "info", "error", "example", "quote"]
    for name in containers:
        assert f"container_{name}_open" in md.renderer.rules
        assert f"container_{name}_close" in md.renderer.rules



# ------------------------------------------------------------
#  Rendering invariants
# ------------------------------------------------------------

def test_to_html_basic_markdown():
    out = to_html("# Title")
    assert "<h1>" in out
    assert "Title" in out


def test_to_html_respects_html_flag():
    md = "<b>bold</b>"
    out1 = to_html(md, allow_html=False)
    out2 = to_html(md, allow_html=True)
    assert out1 != out2
    assert "<b>" not in out1
    assert "<b>" in out2



# ------------------------------------------------------------
#  Container behavior
# ------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "note", "tip", "warning", "danger", "info", "error", "example", "quote"
])
def test_container_blocks_render(name):
    src = f":::{name}\ncontent\n:::"
    out = to_html(src)
    assert "content" in out
    # container plugin wraps content in a <div class="...">
    assert f'class="{name}"' in out or f'class="{name} "' in out


# ------------------------------------------------------------
#  Error handling invariants
# ------------------------------------------------------------

def test_to_html_rejects_non_string():
    with pytest.raises(TypeError):
        to_html(123)

# ------------------------------------------------------------
#  Test core GFM features
# ------------------------------------------------------------
def test_gfm_core_features():
    md = make_markdown_parser()

    # --- Task lists ---
    out = md.render("- [x] done\n- [ ] todo")
    assert 'type="checkbox"' in out
    assert 'checked' in out

    # --- Tables ---
    table = (
        "| A | B |\n"
        "|---|---|\n"
        "| 1 | 2 |\n"
    )
    out = md.render(table)
    assert "<table>" in out
    assert "<td>1</td>" in out

    # --- Footnotes ---
    foot = "Here is a footnote.[^1]\n\n[^1]: Footnote text."
    out = md.render(foot)
    assert "footnote-ref" in out
    assert "footnote-item" in out

    # --- Containers ---
    out = md.render(":::note\nHello\n:::")
    assert '<div class="note">' in out
    assert "</div>" in out

    # --- Strikethrough ---
    out = md.render("~~strike~~")
    assert "<s>strike</s>" in out
