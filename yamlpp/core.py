"""
Core application for the YAMLpp interpreter

(C) Laurent Franceschetti, 2025
"""

import os
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
from io import StringIO
import ast



from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError as Jinja2UndefinedError
from super_collections import super_collect, SuperCollection, SuperDict


from .stack import Stack
from .util import yaml, load_yaml, dequote, get_line_number, validate_node
from .import_modules import get_exports




# --------------------------
# Language fundamentals
# --------------------------

# Type aliases
BlockNode = Dict[str, Any]
ListNode  = List[Any]
Node = Union[BlockNode, ListNode, str, int, float, bool, None] 
KeyOrIndexentry = Tuple[Union[str, int], Node]

# Global functions for Jinja2
GLOBAL_CONTEXT = {
    "getenv": os.getenv
}




class Error(str, Enum):
    VALIDATION = "ValidationError"
    KEY = "KeyNotFound"
    INDEX = "IndexNotFound"
    ARGUMENTS = "ArgumentMismatch"
    # add more categories as needed

class YAMLppError(Exception):
    """
    Custom exception tied to a Ruamel YAML node.
    Extracts line number and line text directly from the node.
    """
    def __init__(self, node, err_type: Error, message: str):
        # Ruamel line numbers are zero-based, so add 1
        self.line_no = get_line_number(node)
        self.err_type = err_type
        self.message = message
        super().__init__(self.__str__())

    def __str__(self):
        return (f"[{self.err_type}] Line {self.line_no}: {self.message}")

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
            raise YAMLppError(f"Key {self.key} points on a scalar or non-recognized type ({type(self.value).__name__})")
        try:
            return self.value[key]
        except (KeyError, IndexError):
            if strict:
                if err_msg is None:
                    if isinstance(key, str):
                        err_msg = f"Structure '{self.key}' does not contain '{key}'"
                    elif isinstance(key, int):
                        err_msg = f"Sequence in '{self.key}' does not contain {key}nth element"
                raise YAMLppError(self.value, Error.KEY, err_msg)
            else:
                return None
            
    def __getitem__(self, key):
        "Same semantics as a dict or list"
        return self.get(key, strict=True)
    
    def __str__(self):
        "Print the entry"
        return(f"{self.key} ->\n{Interpreter.to_yaml(self.value)}")

# --------------------------
# Interpreter
# --------------------------
class Interpreter:
    "The interpreter class that works on the YAMLLpp AST"


    def __init__(self, filename:str=None, source_dir:str=None):
        "Initialize with the YAMLpp source code"
        self._yaml = None
        self._tree = None
        self._dot_tree = None
        if not source_dir:
            # working directory
            self._source_dir = os.getcwd()

        if filename:
            self.load(filename)
        


    def load(self, filename:str, validate:bool=False):
        "Load a YAMLpp file"
        self._source_dir = os.path.dirname(filename)
        self._yamlpp, self._initial_tree = load_yaml(filename)
        if validate:
            validate_node(self._initial_tree)
        self._reset_environment()


    def _reset_environment(self):
        "Reset the Jinja environment"
        # create the interpretation environment
        # variables not found will raise an error
        self._jinja_env = env = Environment(undefined=StrictUndefined)
        env.globals = Stack(env.globals)
        assert isinstance(env.globals, Stack)
        env.globals.push(GLOBAL_CONTEXT)
        env.filters = Stack(env.filters)
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
    def context(self) -> SuperDict:
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
    def jinja_env(self):
        "The jinja environment"
        return self._jinja_env
    
    @property
    def stack(self):
        "The contextual Jinja stack containing the values"
        # return self._stack
        return self.jinja_env.globals
    
    @property
    def source_dir(self) -> str:
        "The import directory"
        return self._source_dir
    
    # -------------------------
    # Rendering
    # -------------------------

    @staticmethod
    def to_yaml(node:Node) -> str:
        "Translate a tree into a YAML string"
        buff = StringIO()
        yaml.dump(node, buff)
        return buff.getvalue()

    
    def render_tree(self) -> Node:
        """
        Render the YAMLpp into a tree
        (it caches the tree and string)

        It returns a dictionary accessible with the dot notation.
        """
        assert len(self.initial_tree) > 0, "Empty yamlpp!"
        self._tree = self.process_node(self.initial_tree)
        assert isinstance(self._tree, (dict, list))
        assert self._tree is not None, "Empty tree!"

        self._yaml = self.to_yaml(self._tree)
        self._dot_tree = super_collect(self._tree)
        return self._dot_tree
    

    @property
    def tree(self) -> Node:
        """
        Return the rendered tree (lazy)

        It returns a list/dictionary, accessible with the dot notation
        (but without the meta data, etc.)
        """
        if self._dot_tree is None:
            self.render_tree()
        assert self._dot_tree is not None, "Failed to regenerate tree!"
        return self._dot_tree
    
        
    
    def dump(self) -> str:
        """
        Render the YAMLpp into YAML
        (Forcing recalculation)
        """
        self.render_tree()
        return self._yaml
    
    @property
    def yaml(self) -> str:
        """
        Return the final yaml code
        (no calculation unless it's the first time)
        """
        if self._yaml is None:
            self.render_tree()
        return self._yaml


    # -------------------------
    # Walking the tree
    # -------------------------

    def evaluate_expression(self, expr: str|Any) -> Node:
        """
        Evaluate a Jinja2 expression string against the stack.
        If the expr is not a string, converts it.
        """
        if not isinstance(expr, str):
            expr = repr(expr)
        template = self.jinja_env.from_string(expr)
        # return template.render(**self.stack)
        r = template.render()
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

    def process_node(self, node: Node) -> Any:
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
            
            result_dict:dict = {}
            result_list:list = []
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
                elif key == ".import":
                    r = self.handle_import(entry)
                elif key == ".module":
                    r = self.handle_module(entry)
                elif key == ".function":
                    r = self.handle_function(entry)
                elif key == ".call":
                    r = self.handle_call(entry)
                elif key == ".export":
                    r = self.handle_export(entry)
                else:
                    # normal YAML key
                    r = {key: self.process_node(value)}
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
            ".else": [...]
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



    def handle_import(self, entry:MappingEntry) -> Node:
        """
        Import of an external file
        """
        filename = self.evaluate_expression(entry.value)
        full_filename = os.path.join(self.source_dir, filename)
        _, data = load_yaml(full_filename)
        return self.process_node(data)
    
    def handle_module(self, entry:MappingEntry) -> None:
        """
        Import a Python module, with variables (function) and filters.
        The import is scoped.
        """
        filename =  self.evaluate_expression(entry.value)
        full_filename = os.path.join(self.source_dir, filename)
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
        assert not isinstance(new_block, SuperCollection)
        new_block['.context'] = assigned_args
        return self.process_node(new_block)


    def handle_export(self, entry:MappingEntry) -> None:
        """
        Exports the subtree into an external file

        block = {
            ".filename": "...",
            ".content": {...} or []
        }
        """
        filename = self.evaluate_expression(entry['.filename'])
        full_filename = os.path.join(self.source_dir, filename)
        tree = self.process_node(entry['.content'])
        yaml_output = self.to_yaml(tree)
        with open(full_filename, 'w') as f:
            f.write(yaml_output)


        
