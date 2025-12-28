"""
Deterministic rendering of text buffers.

This is a key component.
"""
import textwrap


class Indentation(int):
    "Relative indentation in no of units"
    pass



def infer_indent_level(s: str, indent_width: int) -> int:
    """
    Infer the indentation level of a multiline string.
    - s: the multiline string
    - indent_width: number of spaces per indentation unit
    Returns an integer >= 0.
    """
    if not s:
        return 0
    # Split into lines
    lines = s.rstrip().splitlines()
    last = lines[-1]
    # Count leading spaces:
    leading_spaces = len(last) - len(last.lstrip(" "))
    # Compute indentation level:
    return leading_spaces // indent_width


def render_buffer(content: list[str|Indentation], indent_width: int) -> str:
    """
    Deterministic text rendering machine, based on three instructions:

    1. emit a string (explicit)
    2. indent/deindent (explicit)
    3. infer next indentation (implicit)

    
    It renders a text buffer with the rules:

    1. Empty items are ignored
    2. Leading spaces are the current indentation level multiplied by the indent_width.
    3. Explicit: Strings are emitted with leading spaces
    4. Implicit: The indentation level after a string is determined by the leading spaces of its last line.
    5. Explicit: The indentation level before a string can be manually shifted (+1, -1, +2, -2, etc.)
    6. Ruamel chokes on block text (preceded by `|`) that is deindenting. To compensate for that,
       a snippet can start with a dot and spaces, and the dot will then be treated as a space.
    """
    # constants
    SHIFT_SIGNAL = '. '
    REPLACEMENT = ' ' * len(SHIFT_SIGNAL)

    # Remove empty items
    content = [item for item in content if item]
    # create the indented buffer
    indent_level = 0
    indented_buffer = []
    for item in content:
        # print("Indent level:", indent_level)
        if isinstance(item, Indentation):
            # shift instruction
            indent_level += item
        else:
            # emit instruction
            # print("Found line:\n", item)
            # handle the '. ' on first line (to allow right-shift with |)
            if item.startswith(SHIFT_SIGNAL):
                item = REPLACEMENT + item.removeprefix(SHIFT_SIGNAL)
            # indent the string
            spaces = indent_level * indent_width
            line = textwrap.indent(item, spaces * " ")
            indented_buffer.append(line)
            # Retro-propagation: infer the new indentation level from the last one
            indent_level = infer_indent_level(line, indent_width)
            # print("New indentation level:", indent_level)
        # print("---")
    return "\n".join(indented_buffer)
