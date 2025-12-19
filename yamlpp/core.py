"""
Core application for the YAMLpp interpreter

(C) Laurent Franceschetti, 2025
"""

import os
from typing import Any, Dict, List, Optional, Union, Tuple, Self
import ast
from pathlib import Path



from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError as Jinja2UndefinedError
from pprint import pprint

from .stack import Stack
from .util import load_yaml, validate_node, parse_yaml, safe_path
from .util import to_yaml, serialize, get_format, deserialize, normalize, collapse_seq
from .util import CommentedMap, CommentedSeq # Patched versions (DO NOT CHANGE THIS!)
from .error import YAMLppError, Error, JinjaExpressionError, DispatcherError
from .import_modules import get_exports

from .sql import SQLConnection, sql_create_engine, sql_text, sql_query, SQLOperationalError



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

# strings accepted as expressions
STRING_LIKE = str, Path



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
        Get a child node from a node by key, and raise an error if not found.
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
            
    def get_sub_entry(self, key:str|int) -> Self:
        """
        Get a sub-entry with a string key.
        Is used for constructs that incorporate another construct with special semantics
        (like .do)
        """
        try:
            # return an object of the same class
            return self.__class__(key, self[key])
        except (KeyError, IndexError) as e:
            raise YAMLppError(self.value, Error.KEY, e)
            
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

    # The list of allowed construct keywords for the Dispatcher
    # the handlers behave as dunder methods (with same name)
    # '.load' -> self.handle()
    #
    # When you create a new construct:
    #  - Create the handler
    #  - Register it in this list
    CONSTRUCTS = ('.context', '.do', '.foreach', '.switch', '.if', 
                  '.load', '.import', 
                  '.function', '.call', '.export', 
                  '.def_sql', '.exec_sql', '.load_sql')



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
            self._tree = self.render_tree()
            return self.tree

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
            assert isinstance(self._tree, (dict, list)) or self._tree is None
            # assert self._tree is not None, "Empty tree!"
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
        # assert self._tree is not None, "Failed to regenerate tree!"
        return self._tree
    
        
    
   

    # -------------------------
    # Walking the tree
    # -------------------------

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
            new_context = False
            if params_block:
                # self.stack.push({}) # create the scope before doing calculations
                # new_scope = self.get_scope(params_block)
                # self.stack.update(new_scope)
                # self.jinja_env.filters.push({})
                new_context = True

            result_dict = CommentedMap()
            result_list = CommentedSeq()           
            # result_dict:dict = {}
            # result_list:list = []
            for key, value in node.items():
                entry = MappingEntry(key, value)
                # ------
                # Replace with a dispatcher:
                # elif key == ".do":
                #     r = self.handle_do(entry)
                # elif key == ".foreach":
                #     r = self.handle_foreach(entry)
                #     # print("Returned foreach:",)
                # ....
                # ------
                if key in self.CONSTRUCTS:
                    try:
                        r = self._despatch(key, entry)
                    except SQLOperationalError as e:
                        raise YAMLppError(node, Error.SQL, e)
                else:
                    # normal YAML key
                    try:
                        # evaluate the result key (could contain a Jinja2 expression)
                        result_key = self.evaluate_expression(key)
                        # produce the result
                        r = {result_key: self.process_node(value)}
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
            
            if new_context:
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
            # Collapse rules:
            r = [item for item in r if item is not None]
            if len(r):
                return r
            else:
                # This is intentional
                return None


        else:
            return node


    def _despatch(self, keyword:str, entry:MappingEntry) -> Node:
        """
        Despatch the struct to the proper handler (dunder method)

        '.load' -> self.handle_load()
        """
        assert keyword in self.CONSTRUCTS, f"Unknown keyword '{keyword}'"
        
        # find the handler method:
        method_name = f"handle_{keyword[1:]}"
        if hasattr(self, method_name):
            # call the handler
             method = getattr(self, method_name)
        else:
            raise AttributeError(f"Missing handler for {method_name}!")
        # run the method and return the result
        return method(entry)


    def evaluate_expression(self, expr: str) -> Node:
        """
        Evaluate a string expression

        Evaluate a Jinja2 expression string against the stack.
        If the expr is not a string, fail miserably.
        """
        if isinstance(expr, STRING_LIKE):
            str_expr = str(expr)
        else:
            # str_expr = str(expr)
            raise ValueError(f"Value to be evaluated is not a string: '{expr}'")

        if '{' not in str_expr:
            # optimization (the expression is plain str, not Jinja)
            return str_expr
        
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

    

    # -------------------------
    # Specific handlers (after dispatcher)
    # -------------------------
        

    def _get_scope(self, params_block: Dict) -> Dict:
        """
        Evaluate the values from a (parameters) node,
        to create a new scope.
        """
        new_scope: Dict[str, Any] = {}
        if isinstance(params_block, dict):
            for key, value in params_block.items():
                # print("Key:", key)
                assert isinstance(self.stack, Stack), f"the stack is not a Stack but '{type(self.stack).__name__}'"
                # normalize the result, so that it's properly managed as a variable
                new_scope[key] = normalize(self.process_node(value))
        else:
            raise ValueError(f"A parameter block must be a dictionary found: {type(params_block).__name__}")
        
        return new_scope



    def handle_context(self, entry:MappingEntry) -> None:
        """
        .context creates a new block.

        """
        self.stack.push({}) # create the scope before doing calculations
        new_scope = self._get_scope(entry.value)
        # print("New scope:\n", new_scope)
        self.stack.update(new_scope)
        self.jinja_env.filters.push({})
        return None

    def handle_do(self, entry:MappingEntry) -> ListNode:
        """
        Sequence of instructions
        (it will also accept a map)

        Collapse of the result:
            - only 1 result, returns it.
            - no result: returns None
        """
        # print(f"*** DO action ***")
        if isinstance(entry.value, CommentedSeq):
            results: ListNode = []
            for node in entry.value:
                r = self.process_node(node)
                if r:
                    results.append(r)
            return collapse_seq(results)
        elif isinstance(entry.value, CommentedMap):
            # Accept also a map
            # print("Map within a .do:", entry.value)
            return self.process_node(entry.value)
        

    def handle_foreach(self, entry:MappingEntry) -> List[Any]:
        """
        Loop through a sequence or iterable expression

        block = {
            ".values": [var_name, iterable_expr],
            ".do": [...]
        }
        """
        # print("\nFOREACH")
        var_name, iterable_expr = entry[".values"]
        result = self.process_node(iterable_expr)
        # the result was a string; it needs to be converted:
        # iterable = dequote(result)
        iterable = result

        results: List[Any] = []
        for item in iterable:
            local_ctx = {}
            local_ctx[var_name] = item
            self.stack.push(local_ctx)
            # handle the .do block, standardly:
            do_entry = entry.get_sub_entry('.do')
            result = self.handle_do(do_entry)
            results.append(result)
            self.stack.pop()
        return collapse_seq(results)


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



    def handle_load(self, entry:MappingEntry) -> Node:
        """
        Load an external file (YAML or other format)

        In can be either a string (filename), or:
        
        block = {
            ".filename": ...,
            ".format": ... # optional
            ".args": { } # the additional arguments (dictionary)
        }
        """
        # print(".load is recognized", entry.key, entry.value)
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
        # print("Args:", assigned_args)
               

        # create the new block and copy the arguments as context
        actions = function['.do']
        new_block = actions.copy()
        new_block['.context'] = assigned_args
        new_block.move_to_end('.context', last=False) # brigng first
        return self.process_node(new_block)


    def handle_export(self, entry: MappingEntry) -> None:
        """
        Exports the subtree into an external file

        export:
            .filename: ...,
            .format: ... # optional
            .args: { } # the additional arguments
            .do: {...} or []
        """
        filename = self.evaluate_expression(entry['.filename'])
        full_filename = Path(self.source_dir) / filename
        # ✅ Ensure the parent directory exists (CI-safe)
        Path(full_filename).parent.mkdir(parents=True, exist_ok=True)

        format = entry.get('.format')  # get the export format, if there
        kwargs = entry.get('.args') or {}  # arguments
        tree = self.process_node(entry['.do'])

        # work out the actual format, and export
        actual_format = get_format(filename, format)
        file_output = serialize(tree, actual_format, **kwargs)

        with open(full_filename, 'w') as f:
            f.write(file_output)
        assert Path(full_filename).is_file()
        print(f"Exported to: {full_filename} ✅ ")




    def handle_def_sql(self, entry:MappingEntry) -> None:
        """
        Declare an SQL connection (SQL Alchemy)

        See: https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine

        .name: ... # the name by which the engine will be know
        .URL: .... # the string that encodes the dialect, DBAPI and the database location
        .args: ... # additional keyword arguments (optional) 
        """
        name = self.evaluate_expression(entry['.name'])
        url = self.evaluate_expression(entry['.url'])
        kwargs = self.process_node(entry.get('args')) or {}
        self.stack[name] = sql_create_engine(url, **kwargs)


    def _sql_query(self, entry:MappingEntry) -> list[dict]:
        """
        Helper function for performing a query on an entry
        """
        engine_name = self.evaluate_expression(entry['.engine'])
        engine = self.stack[engine_name]
        query = self.evaluate_expression(entry['.query']) or {}
        try:
            rows = sql_query(engine, query)
        except SQLOperationalError as e:
            raise YAMLppError(entry.value, Error.SQL, e)     
        return rows

    def handle_exec_sql(self, entry:MappingEntry) -> None:
        """
        Execute a query on an connection (SQL Alchemy)

        .engine: ... # the name of the engine
        .query:  ... # the query to be executed
        """
        self._sql_query(entry)
        

    def handle_load_sql(self, entry:MappingEntry) -> ListNode:
        """
        Loads data from an SQL connection (SQL Alchemy) as a sequence

        .engine: ... # the name of the engine
        .query:  ... # the query to be executed
        """
        rows = self._sql_query(entry)
        # print("Load SQL was run:\n", rows)
        seq = CommentedSeq()
        for row in rows:
            # Ensure each row is a YAML node, not a plain dict
            seq.append(CommentedMap(row))
        return seq

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