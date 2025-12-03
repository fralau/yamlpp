"""
The terminal client
"""
import sys
import traceback

import argparse



from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


from .core import Interpreter
from .util import serialize

# -------------------------
# General parameters
# -------------------------

OUTPUT_FORMATS = ["yaml", "json", "toml", "python"]

# -------------------------
# Presentation
# -------------------------
console = Console()
err_console = Console(stderr=True)

def format_code(code:str, title:str, language:str='yaml', color:str='green') -> Panel:
    "Make a rich Panel for code (default language is YAML), with title and content"
    colored_title = f"[bold {color}]{title}[/bold {color}]"
    return Panel(
        Syntax(code, language, theme="monokai", line_numbers=True),
        title=colored_title
    )

# -------------------------
# Key-value parsing
# -------------------------

def parse_var(s):
    """
    Parse a key, value pair, separated by '='
    That's the reverse of ShellArgs.

    On the command line (argparse) a declaration will typically look like:
        foo=hello
    or
        foo="hello world"
    """
    items = s.split('=')
    key = items[0].strip() # we remove blanks around keys, as is logical
    if len(items) > 1:
        # rejoin the rest:
        value = '='.join(items[1:])
    else:
        raise ValueError(f"Cannot interpret key-value pair (space between = and value?): {s}")
    return (key, value)


def parse_vars(items):
    """
    Parse a series of key-value pairs and return a dictionary
    """
    d = {}

    if items:
        for item in items:
            key, value = parse_var(item)
            d[key] = value
    return d



# -------------------------
# Main function
# -------------------------

def main():
    parser = argparse.ArgumentParser(
        description="YAML Preprocessor: modules, parameters, env(), and conditional blocks"
    )
    parser.add_argument("file", help="Path to the YAML config file")

    HELP = """
            Arguments to be passed as variables to the pre-processor's environment.
            Set a number of key-value pairs
            (do not put spaces before or after the = sign).
            If a value contains spaces, you should define "
            it with double quotes:
            'foo="this is a sentence". Note that
            meaningful literals are automatically converted to scalars, sequences or maps,
            unless the value
            passed is surrounded by quotes (e.g. `--set a="'5'"`).
    """
    parser.add_argument("--set",
                        metavar="KEY=VALUE",
                        nargs='+',
                        help=HELP)
    parser.add_argument("-o", "--output", help="Write rendered output to file")
    parser.add_argument("-i", "--initial", action="store_true", help="Show original YAML before processing")
    parser.add_argument("-d", "--debug", action="store_true", 
                        help="Give traceback exception in case of error")
    parser.add_argument(
        "-f", "--format",
        choices=OUTPUT_FORMATS,
        default="yaml",
        help="Output format (default: yaml)"
    )
    args = parser.parse_args()


    try:
        # Read the key/value arguments to be passed
        variables = parse_vars(args.set)
        
        # load YAMLpp
        interpreter = Interpreter(args.file)

        # update the environment with the passed variables
        interpreter.set_context(variables)
        if len(variables):
            output = serialize(interpreter.context)
            err_console.print(format_code(output, title='Initial context'))
        
        # Show raw
        if args.initial:
            err_console.print(format_code(interpreter.yamlpp, title="Original YAML", color="magenta"))
        # then render:
        interpreter.render_tree()
    except Exception as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        if args.debug:
            traceback.print_exc()   # print on stderr
        raise SystemExit(1)


    # -------------------
    # Output
    # -------------------
    rendered = interpreter.dumps(format=args.format)

    if args.output:
        with open(args.output, "w") as f:
            f.write(rendered)
        err_console.print(f"[bold yellow]Written to {args.output}[/bold yellow]")
    elif sys.stdout.isatty():
        # Pretty print if interactive
        console.print(format_code(rendered, 
                                    title=f"Rendered {args.format.upper()}",
                                    language=args.format))
    else:
        # piped into an output file:
        print(rendered)

