"""
Host interface for Protein

It provides decorators for functions defined in an external Python module 
for the Jinja environment used in Protein expressions.


"""
import os
from pathlib import Path
from dataclasses import dataclass, field
import importlib.util




@dataclass
class ModuleEnvironment:
    """
    The static environment in which host (Python) functions are executing.

    This is enforcing a rule:

    > The host must never perform work that the Protein engine is not aware about.

    This is not a stylistic preference.
    It’s a metaphysical constraint built into a dualist architecture (Protein / host).
    """
    source_dir: Path # this is the boundary of the host's universe

    variables: dict[str, callable] = field(default_factory=dict)
    filters: dict[str, callable] = field(default_factory=dict)

    def __post_init__(self):
        "Normalize source_dir to a Path"
        self.source_dir = Path(self.source_dir)

    

    def export(self, func:callable) -> callable:
        """
        Decorator: Mark a function as an exported function to the Jinja2 environment of the
        YAML preprocessor.
        """
        self.variables[func.__name__] = func
        return func

    def filter(self, func:callable) -> callable:
        """
        Decorator: Mark a function as an exported filter to the Jinja2 environment of the
        YAML preprocessor.
        """
        self.filters[func.__name__] = func
        return func
    
# --------------------------
# Module loading and stack
# --------------------------

def load_module(pathname: str):
    if not os.path.isfile(pathname):
        raise FileNotFoundError(f"Module file '{pathname}' is not found.")
    spec = importlib.util.spec_from_file_location("yamlpp_dynamic_module", pathname)
    if spec is None:
        raise OSError(f"Module '{pathname}' is not properly formed.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def get_exports(module_path:str, source_dir:str="") -> tuple[dict,dict]:
    """
    Get the explicitely decorated functions/filters from a module
    (see .decorator.py)
    """
    module = load_module(module_path)
    load_function = getattr(module, 'define_env')
    env = ModuleEnvironment(source_dir=source_dir)
    load_function(env)
    return env.variables, env.filters