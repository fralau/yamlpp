

from pathlib import Path
from protein import Interpreter
from protein.test import interp, print_yaml


CURRENT_DIR = Path(__file__).resolve().parent



def test_static_site_generator(tmp_path):
    """
    Static site generator
    """


    PROGRAM = CURRENT_DIR / "build_static_site.ypp"

    #
    # ------------------------------------------------------------
    # 1. Create external DATA files (content, templates, theme)
    # ------------------------------------------------------------
    #

    PAGES_DIR = CURRENT_DIR / "pages"
    TEMPLATES_DIR = CURRENT_DIR / "templates"
    SITE_DIR = CURRENT_DIR / "site"


    #
    # ------------------------------------------------------------
    # 3. Run Protein in the temporary directory
    # ------------------------------------------------------------
    #
    i = Interpreter(PROGRAM)
    assert i.source_dir == str(CURRENT_DIR)
    i.render_tree()
    i.print()
 

    #
    # ------------------------------------------------------------
    # 4. Assertions on generated artifacts
    # ------------------------------------------------------------
    #

    assert (SITE_DIR / "styles.css").exists()
    assert (SITE_DIR / "page1.html").exists()
    assert (SITE_DIR / "page2.html").exists()
    assert (SITE_DIR / "index.html").exists()

    html1 = (SITE_DIR / "page1.html").read_text()
    assert "Page One" in html1
    assert "This is page one." in html1

    html2 = (SITE_DIR / "page2.html").read_text()
    assert "Page Two" in html2
    assert "This is page two." in html2
