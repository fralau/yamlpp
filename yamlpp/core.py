"""
Core application for the YAMLpp interpreter

(C) Laurent Franceschetti, 2025
"""

import os
from typing import Any, Dict, List, Optional, Union, Tuple
import ast



from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError as Jinja2UndefinedError
from pprint import pprint

from .stack import Stack
from .util import load_yaml, validate_node, parse_yaml, safe_path
from .util import to_yaml, serialize, get_format, deserialize
from .util import CommentedMap, CommentedSeq # Patched versions (DO NOT CHANGE THIS!)
from .error import YAMLppError, Error, JinjaExpressionError
from .import_modules import get_exports



# --------------------------
# Language fundamentals
# --------------------------
assert CommentedMap.is_patched, "I need the patched version of CommentedMap in .util"

# Type aliases
BlockNode = Dict[str, Any]
ListNode  = List[Any]
Node = Union[BlockNode, ListNode, str, int, float, bool, None] 
KeyOrIndexentry = Tuple[Union[str, int], Node]

# Global functions for Jinja2

import keyring

GLOBAL_CONTEXT = {
    "getenv": os.getenv,
    "get_password": keyring.get_password
}


class MappingEntry:
    """
    A key value entry
    """

    def __init__(self, key:str, value: Node):
        "Initialize"
        self.key = key
        self.value = value

    @property
    def attributes(self):
        """
        Get the attributes of the current entry.
        It works only on a dictionary value.
        """
        try:
            return list(self.value.keys())
        except AttributeError:
            raise ValueError("This mapping entry does not have attribues")

    def get(self, key:str|int, err_msg:str=None, strict:bool=False) -> Node:
        """
        Get a child from a node by key, and raise an error if not found.
        The value of entry must be either dict (it's an attribute) or list.
        """
        if not isinstance(self.value, (list, dict)):
            # it's probably a scalar
            return None
            # raise YAMLppError(self.value, Error.KEY,
            #             f"Key {self.key} points on a scalar or non-recognized type ({type(self.value).__name__})")
        try:
            return self.value[key]
        except (KeyError, IndexError):
            if strict:
                if err_msg is None:
                    if isinstance(key, str):
                        err_msg = f"Map '{self.key}' does not contain '{key}'"
                    elif isinstance(key, int):
                        err_msg = f"Sequence in {self.key}' does not contain {key}nth element"
                raise YAMLppError(self.value, Error.KEY, err_msg)
            else:
                return None
            
    def __getitem__(self, key):
        "Same semantics as a dict or list"
        return self.get(key, strict=True)
    
    def __str__(self):
        "Print the entry"
        return(f"{self.key} ->\n{to_yaml(self.value)}")

# --------------------------
# Interpreter
# --------------------------
class Interpreter:
    "The interpreter class that works on the YAMLLpp AST"


    def __init__(self, filename:str=None, source_dir:str=None,
                 functions:dict={}, filters:dict={}):
        """
        Initialize with the YAMLpp source code

        Arguments
        ---------
        filename: source file from where the YAML source will be read.
        source_dir: source directory (if different from the filename's directory)
        functions: a dictionary of functions that will update the GLOBALS.
        filters: a dictionary of filters that will update the filters
        """
        self._tree = None
        self._dirty = True
        self._functions = functions
        self._filters = filters
        if not source_dir:
            # working directory
            self._source_dir = os.getcwd()

        if filename:
            self.load(filename)
        else:
            # create a Jinja environment nothing in it
            self._source_dir = source_dir
            self._reset_environment()
        
    @property
    def is_dirty(self) -> bool:
        """
        A modified tree is "dirty"
        and must be rendered again
        """
        try:
            return self._dirty
        except AttributeError:
            return ValueError("Tree was never loaded")
        
    def dirty(self):
        """
        (verb) Make the tree dirty (i.e. say that it must be rendered again). 
        """
        self._dirty = True


    def load(self, source:str, 
             is_text:bool=False, 
             validate:bool=False,
             render:bool=True):
        """
        Load a YAMLpp file (by default, source is the filename)

        Arguments:

        - source: the filename or text
        - is_text: set to True, if it is text
        - validate: submit the YAML source to a schema validation
            (effective, but less helpful in case of error)
        - render: interpret the YAMLpp and generate the YAML (default: yes)
            Set to False, to opt-out of rendering for modification of the tree or debugging.
        """
        self.dirty()
        if not is_text:
            self._source_dir = os.path.dirname(source)
        self._yamlpp, self._initial_tree = load_yaml(source, is_text)
        if validate:
            validate_node(self._initial_tree)
        self._reset_environment()

        if render:
            self.render_tree()

    def load_text(self, text:str, render:bool=True):
        """
        Load text (simplified)

        Arguments:
        - text: the string
        - render: interpret the YAMLpp and generate the YAML (default: yes)
            Set to False, to opt-out of rendering for modification of the tree or debugging.
        """
        return self.load(text, is_text=True, render=render)



    def _reset_environment(self):
        "Reset the Jinja environment"
        # create the interpretation environment
        # variables not found will raise an error
        # NOTE: globals and filters are NO LONGER pure dictionaries, but a stack of dictionaries
        self._jinja_env = env = Environment(undefined=StrictUndefined)
        env.globals = Stack(env.globals)
        assert isinstance(env.globals, Stack)
        env.globals.push(GLOBAL_CONTEXT)
        env.globals.update(self._functions)
        env.filters = Stack(env.filters)
        env.filters.update(self._filters)
        assert isinstance(env.filters, Stack)

    # -------------------------
    # Properties
    # -------------------------
    @property
    def initial_tree(self):
        "Return the initial tree (Ruamel)"
        if self._initial_tree is None:
            raise ValueError("Initial tree is not initialized")
        return self._initial_tree
        
    @property
    def context(self) -> Node:
        "Return the top-level .context section or None"
        # print("INITIAL TREE")
        # print(self.initial_tree)
        return self.initial_tree.get('.context')

    @property
    def yamlpp(self) -> str:
        "The source code"
        if self._yamlpp is None:
            raise ValueError("No source YAMLpp file loaded!")
        return self._yamlpp
    
    @property
    def jinja_env(self) -> Environment:
        "The jinja environment (containes globals and filters)"
        return self._jinja_env
    
    @property
    def stack(self):
        "The contextual Jinja stack containing the values"
        # return self._stack
        return self.jinja_env.globals
    
    @property
    def source_dir(self) -> str:
        "The source directory (where all YAML and other files are located)"
        return self._source_dir

    # -------------------------
    # Preprocessing
    # -------------------------
    def set_context(self, arguments:dict):
        """
        Update the first '.context' of the initial tree with a dictionary (key, value pairs).

        Literal are turned into objects (strings remain strings).
        """
        for key, value in arguments.items():
                arguments[key] = parse_yaml(value)
        # print("Variables (after):", arguments)
        itree = self.initial_tree
        if isinstance(itree, CommentedSeq):
            # Special case: the tree starts with a sequence
            new_start = CommentedMap({
                '.context': arguments,
                '.do': itree
            })
            self.initial_tree = new_start
        else:
            # Usual case: a map
            context = itree.get('.context', CommentedMap())
            context.update(arguments)
            itree['.context'] = context

    # -------------------------
    # Rendering
    # -------------------------

    
    def render_tree(self) -> Node:
        """
        Render the YAMLpp into a tree
        (it caches the tree and string)

        It returns a dictionary accessible with the dot notation.
        """
        if self.is_dirty:
            assert len(self.initial_tree) > 0, "Empty yamlpp!"
            self._tree = self.process_node(self.initial_tree)
            assert isinstance(self._tree, (dict, list))
            assert self._tree is not None, "Empty tree!"
            self._dirty = False
        return self._tree
    

    @property
    def tree(self) -> Node:
        """
        Return the rendered tree (lazy)

        It returns a list/dictionary, accessible with the dot notation
        (but without the meta data, etc.)
        """
        if self._tree is None:
            self.render_tree()
        assert self._tree is not None, "Failed to regenerate tree!"
        return self._tree
    
        
    
   

    # -------------------------
    # Walking the tree
    # -------------------------

    def evaluate_expression(self, expr: str|Any) -> Node:
        """
        Evaluate an expression

        Evaluate a Jinja2 expression string against the stack.
        If the expr is not a string, converts it.
        """
        if isinstance(expr, str):
            str_expr = expr
        else:
            str_expr = repr(expr)
        template = self.jinja_env.from_string(str_expr)
        # return template.render(**self.stack)
        try:
            r = template.render()
        except Exception as e:
            raise JinjaExpressionError(expr, e)
        # print("Evaluate", expr, "->", r, ">", type(r).__name__)
        try:
            # we need to evaluate the expression if possible
            return ast.literal_eval(r)
        except (ValueError, SyntaxError):
            return r


    def get_scope(self, params_block: Dict) -> Dict:
        """
        Evaluate the values from a (parameters) node,
        to create a new scope.
        """
        new_scope: Dict[str, Any] = {}
        if isinstance(params_block, dict):
            for key, value in params_block.items():
                # print("Key:", key)
                assert isinstance(self.stack, Stack), f"the stack is not a Stack but '{type(self.stack).__name__}'"
                new_scope[key] = self.process_node(value)
        else:
            raise ValueError(f"A parameter block must be a dictionary found: {type(params_block).__name__}")
        
        return new_scope     

    def process_node(self, node: Node) -> Node:
        """
        Process a node in the tree
        Dispatch a YAMLpp node to the appropriate handler.
        """
        # print("*** Type:", node, "***", type(node).__name__)
        # assert isinstance(self.stack, Stack), f"The stack is not a Stack but '{type(self.stack).__name__}':\n{node}'"
        if node is None:
            return None;
        elif isinstance(node, str):
            # String
            try:
                return self.evaluate_expression(node)
            except Jinja2UndefinedError as e:
                raise ValueError(f"Variable error in string node '{node}': {e}")
            
        
        elif isinstance(node, dict):
            # Dictionary nodes
            # print("Dictionary:", node)

            # Process the .context block, if any (local scope)
            params_block = node.get(".context")
            if params_block:
                new_scope = self.get_scope(params_block)
                self.stack.push(new_scope)
                self.jinja_env.filters.push({})

            result_dict = CommentedMap()
            result_list = CommentedSeq()           
            # result_dict:dict = {}
            # result_list:list = []
            for key, value in node.items():
                entry = MappingEntry(key, value)
                if key == ".context":
                    # Do not include
                    r = None
                elif key == ".do":
                    r = self.handle_do(entry)
                elif key == ".foreach":
                    r = self.handle_foreach(entry)
                    # print("Returned foreach:",)
                elif key == ".switch":
                    r = self.handle_switch(entry)
                elif key == ".if":
                    r = self.handle_if(entry)
                elif key == ".insert":
                    r = self.handle_insert(entry)
                elif key == ".import":
                    r = self.handle_import(entry)
                elif key == ".function":
                    r = self.handle_function(entry)
                elif key == ".call":
                    r = self.handle_call(entry)
                elif key == ".export":
                    r = self.handle_export(entry)
                else:
                    # normal YAML key
                    try:
                        r = {key: self.process_node(value)}
                    except JinjaExpressionError as e:
                        raise YAMLppError(node, Error.EXPRESSION, str(e))
                # Decide what to do with the result
                # Typically, .foreach returns a list
                if r is None:
                    continue
                elif isinstance(r, dict):
                    result_dict.update(r)
                elif isinstance(r, list):
                    result_list += r
                else:
                    result_list.append(r)
            
            if params_block:
                # end of the scope, for these parameters
                self.stack.pop()
                self.jinja_env.filters.pop()

            if len(result_dict):
                return result_dict
            elif len(result_list):
                return result_list

        elif isinstance(node, list):
            # print("List:", node)
            r = [self.process_node(item) for item in node]
            r = [item for item in r if item is not None]
            if len(r):
                return r


        else:
            return node


    # -------------------------
    # Specific handlers (after dispatcher)
    # -------------------------

    def handle_do(self, entry:MappingEntry) -> ListNode:
        """
        Sequence of instructions
        """
        print(f"*** DO action ***")
        results: ListNode = []
        for node in entry.value:
            results.append(self.process_node(node))
        return results

    def handle_foreach(self, entry:MappingEntry) -> List[Any]:
        """
        Loop

        block = {
            ".values": [var_name, iterable_expr],
            ".do": [...]
        }
        """
        # print("\nFOREACH")
        var_name, iterable_expr = entry[".values"]
        result = self.evaluate_expression(iterable_expr)
        # the result was a string; it needs to be converted:
        # iterable = dequote(result)
        iterable = result

        results: List[Any] = []
        for item in iterable:
            local_ctx = {}
            local_ctx[var_name] = item
            self.stack.push(local_ctx)
            do = entry[".do"]
            results.append(self.process_node(do))
            self.stack.pop()
        return results


    def handle_switch(self, entry:MappingEntry) -> Node:
        """
        block = {
            ".expr": "...",
            ".cases": { ... },
            ".default": [...]
        }
        """
        expr = entry[".expr"]
        expr_value = self.evaluate_expression(expr)
        cases: Dict[Any, Any] = entry[".cases"]
        if expr_value in cases:
            return self.process_node(cases[expr_value])
        else:
            return self.process_node(cases.get(".default"))


    def handle_if(self, entry:MappingEntry) -> Node:
        """
        And if then else structure

        block = {
            ".cond": "...",
            ".then": [...],   
            ".else": [...]. # optional
        }
        """
        r = self.evaluate_expression(entry['.cond'])
        # transform the Jinja2 string into a value that can be evaluated
        # condition = dequote(r)
        condition = r
        if condition:
            r = self.process_node(entry['.then'])
        else:
            r = self.process_node(entry.get(".else"))
        # print("handle_if:", r)
        return r



    def handle_insert(self, entry:MappingEntry) -> Node:
        """
        Insert of an external file

        In can be either a string (filename), or:
        
        block = {
            ".filename": ...,
            ".format": ... # optional
            ".args": { } # the additional arguments (dictionary)
        }
        """
        # print(".insert is recognized", entry.key, entry.value)
        if isinstance(entry.value, str):
            filename = self.evaluate_expression(entry.value)
            format = None
            kwargs = {}
        
        else:
            filename = self.evaluate_expression(entry['.filename'])
            format = entry.get('.format') # get the export format, if there 
            kwargs = entry.get('.args') or {} # arguments
        
        try:
            full_filename = safe_path(self.source_dir, filename)
        except FileNotFoundError as e:
            raise YAMLppError(entry.value, Error.FILE, e)  
        actual_format = get_format(filename, format)
        with open(full_filename, 'r') as f:
            text = f.read()
        # read the file
        data = deserialize(text, actual_format, **kwargs)
        # _, data = load_yaml(full_filename)
        return self.process_node(data)
    
    def handle_import(self, entry:MappingEntry) -> None:
        """
        Import a Python module, with variables (function) and filters.
        The import is scoped.
        """
        filename =  self.evaluate_expression(entry.value)
        try:
            full_filename = safe_path(self.source_dir, filename)
        except FileNotFoundError as e:
            raise YAMLppError(entry.value, Error.FILE, e)  
        # full_filename = os.path.join(self.source_dir, filename)
        variables, filters = get_exports(full_filename)
        # note how we use update(), since we add to the local scope:
        self.jinja_env.globals.update(variables)
        self.jinja_env.filters.update(filters)
        return None

    
    def handle_function(self, entry:MappingEntry) -> None:
        """
        Create a function
        A function is a block with a name, arguments and a sequence, which returns a subtree.

        block = {
            ".name": "",
            ".args": [...],
            ".do": [...]
        }
        """
        name = entry['.name']
        print("Function created with its name!", name)
        self.stack[name] = entry.value
        return None

        
        

    def handle_call(self, entry:MappingEntry) -> Node:
        """
        Call a function, with its arguments
        block = {
            ".name": "",
            ".args": {},
        }
        """
        name = entry['.name']
        # print(f"*** CALLING {name} ***")
        try:
            function = MappingEntry(name, self.stack[name])
        except KeyError:
            raise YAMLppError(entry, Error.KEY, f"Function '{name}' not found!")
        # assign the arguments
        
        formal_args = function['.args']
        args = entry['.args']
        if len(args) != len(formal_args):
            raise YAMLppError(entry, 
                              Error.ARGUMENTS,
                              f"No of arguments not matching, expected {len(formal_args)}, found {len(args)}")
        assigned_args = dict(zip(formal_args, args))
        # print("Keys:", assigned_args)
               

        # create the new block and copy the arguments as context
        actions = function['.do']
        new_block = actions.copy()
        new_block['.context'] = assigned_args
        return self.process_node(new_block)


    def handle_export(self, entry:MappingEntry) -> None:
        """
        Exports the subtree into an external file

        block = {
            ".filename": ...,
            ".format": ... # optional
            ".args": { } # the additional arguments
            ".do": {...} or []
        }
        """
        filename = self.evaluate_expression(entry['.filename'])
        full_filename = os.path.join(self.source_dir, filename)
        format = entry.get('.format') # get the export format, if there 
        kwargs = entry.get('.args') or {} # arguments
        tree = self.process_node(entry['.do'])
        # work out the actual format, and export
        actual_format = get_format(filename, format)
        file_output = serialize(tree, actual_format, **kwargs)
        with open(full_filename, 'w') as f:
            f.write(file_output)

    # -------------------------
    # Output
    # -------------------------
        
    @property
    def yaml(self) -> str:
        """
        Return the final yaml output
        (it supports a round trip)
        """
        tree = self.render_tree()
        return to_yaml(tree)

    
    
    def dumps(self, format:str) -> str:
        "Serialize the output into one of the supported serialization formats"
        tree = self.render_tree()
        return serialize(tree, format)