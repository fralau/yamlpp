"""
A sample module

(module.py)
"""
from pathlib import Path
import glob as _glob

from markdown_it import MarkdownIt

from protein import ModuleEnvironment


# Directory of the current Protein file
PROTEIN_FILE_DIR = Path(__file__).resolve().parent



def define_env(env: ModuleEnvironment):
    "Define your functions, filters and variables here"

    @env.export
    def glob(pattern: str) -> list[str]:
        """
        Minimal, predictable glob function.

        - Accepts a shell-style glob pattern (e.g. 'content/*.md')
        - Resolves relative patterns from the module's source directory
        - Returns paths relative to the module's source directory
        - Raises an error if the pattern attempts to escape the module directory
        """
        base = env.source_dir
        pattern_path = Path(pattern)

        # Resolve relative patterns inside the module's universe
        if not pattern_path.is_absolute():
            pattern_path = base / pattern_path

        # SECURITY: ensure the *pattern itself* does not escape
        try:
            pattern_path.resolve().relative_to(base)
        except ValueError:
            raise ValueError(f"glob pattern escapes module directory: {pattern!r}")

        results = []

        for match in _glob.glob(str(pattern_path)):
            abs_path = Path(match).resolve()

            # SECURITY: ensure each match is inside the module universe
            try:
                rel = abs_path.relative_to(base)
            except ValueError:
                raise ValueError(f"glob result escapes module directory: {abs_path}")

            results.append(str(rel))

        return sorted(results)



    # Create a single parser instance (fast, reusable)
    _md = MarkdownIt()

    @env.export
    def render_markdown_to_html(s: str) -> str:
        """
        Convert Markdown text to HTML using markdown-it-py.

        - Deterministic output
        - Safe for use inside Protein templates
        """
        if not isinstance(s, str):
            raise TypeError("render_markdown_to_html expects a string")

        return _md.render(s)


    @env.export
    def correct_page(page: dict, author:str) -> dict:
        """
        Fix a page to make it more robust
        """
        if "filename" not in page:
            raise KeyError(f"Page does not have a filename: { page }")
        else:
            filename = page["filename"]
            stem = Path(filename).stem

        if "meta" not in page:
            page["meta"] = {}

        if "title" not in page["meta"]:
            page["meta"]["title"] = stem.replace("_", " ").capitalize()

        if "slug" not in page["meta"]:
            page["meta"]["slug"] = stem
        
        if "author" not in page["meta"]:
            page["meta"]["author"] = author
        
        if not page["text"]:
            raise KeyError(f"Page {stem} does not have a body")
        return page