"""
Core application for the YAMLpp interpreter

(C) Laurent Franceschetti, 2025

"""

import os, sys
from typing import Any, Dict, List, Optional, Union, Tuple, Self
import ast
from enum import Enum
from pathlib import Path
# import textwrap
from collections.abc import Sequence, Mapping




from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError as Jinja2UndefinedError
from pprint import pprint

from .stack import Stack
from .util import load_yaml, validate_node, parse_yaml, safe_path, print_yaml 
from .util import check_name, get_full_filename
from .util import to_yaml, serialize, get_format, deserialize, normalize, collapse_seq, collapse_maps
from .util import CommentedMap, CommentedSeq # Patched versions (DO NOT CHANGE THIS!)
from .util import extract_identifier
from .buffer import render_buffer, Indentation
from .error import YAMLppError, Error, JinjaExpressionError, DispatcherError
from .import_modules import get_exports


from .sql import sql_create_engine, sql_query, SQLOperationalError, osquery


# --------------------------
# Language fundamentals
# --------------------------
assert CommentedMap.is_patched, "I need the patched version of CommentedMap in .util"

# Type aliases
BlockNode = Dict[str, Any]
ListNode  = List[Any]
Node = Union[BlockNode, ListNode, str, int, float, bool, None] 
KeyOrIndexentry = Tuple[Union[str, int], Node]

ALLOWED_NODE_TYPES = dict, list, CommentedMap, CommentedSeq
ALL_NODE_TYPES = ALLOWED_NODE_TYPES + (str, int, float, bool, type(None))   

# Global functions for Jinja2

import keyring
GLOBAL_CONTEXT = {
    "getenv": os.getenv, # function
    "get_password": keyring.get_password, # function
    "osquery": osquery, # function 
        }


# strings accepted as expressions
STRING_LIKE = str, Path



# class Indentation(int):
#     "Relative indentation in no of units"
#     pass


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

    def get(self, key:str|int, default:Any=None, 
            err_msg:str=None, strict:bool=False) -> Node:
        """
        Get a child node from a node by key.
        The value of entry must be either dict (it's an attribute) or list.

        If strict is True, it raises an error if not found.
        """
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
                return default
            
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
    CONSTRUCTS = ('.local','.define',
                  '.do', '.foreach', '.switch', '.if', 
                  '.load', '.import', '.import_module', 
                  '.function', '.call',  
                  '.def_sql', '.exec_sql', '.load_sql',
                  '.export', '.open_buffer', '.write_buffer', '.save_buffer',
                  '.print')



    def __init__(self, filename:str=None, source_dir:str=None,
                 functions:dict=None, filters:dict=None, render:bool=True,
                 is_module:bool=False):
        """
        Initialize with the YAMLpp source code

        Arguments
        ---------
        filename: source file from where the YAML source will be read.
        source_dir: source directory (if different from the filename's directory)
        functions: a dictionary of functions that will update the GLOBALS.
        filters: a dictionary of filters that will update the filters
        render: render the file (default: True)
        is_module: if True, the functions objects are kept in the tree  (default: False)
        """
        self._tree = None
        self._dirty = True
        self._functions = functions if functions is not None else {}
        self._filters = filters if filters is not None else {}

        self._source_file = filename
        self._is_module = is_module
        
        # working directory
        self._source_dir = source_dir

        if filename:
            self.load(filename, render=render)
        else:
            # create a Jinja environment nothing in it
            # self._source_dir = source_dir
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
            if not self._source_dir:
                # the name of source, or (last resort) the current dir
                self._source_dir = os.path.dirname(source)
        if not self._source_dir:
            self._source_dir = os.getcwd()
        self._yamlpp, self._initial_tree = load_yaml(source, is_text)

        if validate:
            validate_node(self._initial_tree)

        # set the source file (if defined)
        if not is_text:
            self._source_file = source
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


    def load_tree(self, tree:Node):
        "Load a tree into the environment"
        self._initial_tree = tree
        self._reset_environment()
        if not self._source_dir:
            self._source_dir = os.getcwd()


    def _reset_environment(self):
        env = Environment(undefined=StrictUndefined)

        # Copy Jinja built-ins into a fresh dict
        base_globals = dict(env.globals)
        base_filters = dict(env.filters)

        # Wrap the copies in your Stack
        env.globals = Stack(base_globals)
        env.filters = Stack(base_filters)

        # Push your own global context (copy!)
        env.globals.push(GLOBAL_CONTEXT.copy())

        # Add interpreter-specific functions/filters
        env.globals.update(self._functions)
        env.globals['__SOURCE_FILE__'] = self.source_file
        env.filters.update(self._filters)

        env.globals.push({})  # initial empty frame for the stack
        env.filters.push({})  # initial empty frame for the filters

        self._jinja_env = env


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
    def local(self) -> Node:
        "Return the top-level .local section or None"
        # print("INITIAL TREE")
        # print(self.initial_tree)
        return self.initial_tree.get('.local')

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
        """
        The stack used to traverse the lexical tree (YAML).

        NOTE: 
            It is important to keep in mind that the YAML tree _is_ YAMLpp's lexical structure.
            This stack is only the tool used to traverse the tree.

            (This is NOT an execution stack, in the traditional way. Execution is done by Jinja.)
        """
        # return self._stack
        return self.jinja_env.globals
    
    @property
    def source_dir(self) -> str:
        "The source/working directory (where all YAML and other files are located)"
        return self._source_dir
    
    @property
    def source_file(self) -> str:
        "The source file (if it exists)"
        return self._source_file

    # -------------------------
    # Preprocessing
    # -------------------------
    def set_frame(self, arguments:dict):
        """
        Update the first '.local' of the initial tree with a dictionary (key, value pairs).

        Literals are turned into objects (strings remain strings).
        """
        for key, value in arguments.items():
                arguments[key] = parse_yaml(value)
        # print("Variables (after):", arguments)
        itree = self.initial_tree
        if isinstance(itree, CommentedSeq):
            # Special case: the tree starts with a sequence
            new_start = CommentedMap({
                '.local': arguments,
                '.do': itree
            })
            self.initial_tree = new_start
        else:
            # Usual case: a map
            context = itree.get('.local', CommentedMap())
            context.update(arguments)
            itree['.local'] = context

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
            # print("Initial tree:", self.initial_tree)
            self._tree = self.process_node(self.initial_tree)
            assert isinstance(self._tree, ALLOWED_NODE_TYPES) or self._tree is None, f"Tree is {type(self._tree).__name__}"
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

            # Process the .local block, if any (local scope)
            params_block = node.get(".local")
            new_context = False
            if params_block:
                new_context = True

            result_dict = CommentedMap()
            result_list = CommentedSeq()           
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
                        self.raise_error(node, Error.SQL, e)
                else:
                    # normal YAML key
                    try:
                        # evaluate the result key (could contain a Jinja2 expression)
                        result_key = self.evaluate_expression(key)
                        # produce the result
                        r = {result_key: self.process_node(value)}
                    except JinjaExpressionError as e:
                        self.raise_error(node, Error.EXPRESSION, str(e))
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
        err_intro = f"{keyword} > " # for error handling
        try:
            return method(entry)
        except YAMLppError as e:
            if e.line_no != 0:
                self.raise_error(e.node, e.err_type, err_intro + e.message)
            else:
                self.raise_error(entry.value, e.err_type, err_intro + e.message)
        except ValueError as e:
            self.raise_error(entry.value, Error.VALUE, e)
        except IndexError as e:
            self.raise_error(entry.value, Error.INDEX, e)
        except TypeError as e:
            self.raise_error(entry.value, Error.TYPE, e)
        except Exception as e:
            self.raise_error(entry.value, Error.OTHER, e)

    def evaluate_expression(self, expr: str) -> Node:
        """
        Evaluate a string expression

        Evaluate a Jinja2 expression string against the stack.
        If the expr is not a string, fail miserably.
        """
        if expr is None:
            return None
        elif isinstance(expr, (int, float)):
            return expr
        elif isinstance(expr, STRING_LIKE):
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
            print("Error evaluating expression:", expr, file=sys.stderr)
            for i, frame in enumerate(self.stack):
                print(f"  {i}: {frame}", file=sys.stderr)
            raise JinjaExpressionError(expr, e)
        # print("Evaluate", expr, "->", r, ">", type(r).__name__)
        try:
            # we need to evaluate the expression if possible
            return ast.literal_eval(r)
        except (ValueError, SyntaxError):
            return r

    def raise_error(self, node, err_type: Error, message: str):
        """
        Raises a YAMLpp error.
        Extracts line number and line text directly from the node.
        Automatically adds the last loaded filename to the message
        """ 
        raise YAMLppError(node, err_type, message, self.stack['__SOURCE_FILE__'])

    # -------------------------
    # Specific handlers (after dispatcher)
    # -------------------------
        

    def _get_frame(self, params_block: Dict) -> Dict:
        """
        Evaluate the values from a (parameters) node,
        to create a new frame (or a part of a frame).
        """
        new_frame: Dict[str, Any] = {}
        if params_block is None:
            params_block = {}
        elif isinstance(params_block, dict):
            for key, value in params_block.items():
                # print("Key:", key)
                assert isinstance(self.stack, Stack), f"the stack is not a Stack but '{type(self.stack).__name__}'"
                # normalize the result, so that it's properly managed as a variable
                new_frame[key] = normalize(self.process_node(value))
        else:
            raise ValueError(f"A frame must be a dictionary found: {type(params_block).__name__}")
        
        return new_frame


    # ---------------------
    # Printing
    # ---------------------
    def handle_print(self, entry:MappingEntry) -> None:
        """
        Print the text to stderr
        """
        output = self.evaluate_expression(entry.value)
        print(output, file=sys.stderr)

    # ---------------------
    # Variables
    # ---------------------

    def handle_local(self, entry:MappingEntry) -> None:
        """
        Creates a new frame (scope) on the stack, and adds variables.

        Note: you cannot reuse variables defined in the same .local block.

        .local:
            ....

        """
        self.stack.push({}) # create the frame before doing calculations
        # print("Value:\n", entry.value)
        result = self.process_node(entry.value)
        new_frame = self._get_frame(result)
        # print("New scope:\n", new_scope)
        self.stack.update(new_frame)
        self.jinja_env.filters.push({})
        if self._is_module:
            # in a module, you return the result of the evaluation
            return result
        else:
            return None
    
    def handle_define(self, entry:MappingEntry) -> None:
        """
        Defines new variables, without creating a new scope.

        Note: you cannot reuse variables defined in the same .export block.

        It is useful
        - when used before the `.local`in an imported file: for exporting variables
          to the parent context.
        - after a .local, for defining new variables, without changing scope
        """# create the scope before doing calculations
        # print("Value:\n", entry.value)
        result = self.process_node(entry.value)
        block = self._get_frame(result)
        # print("New scope:\n", new_scope)
        self.stack.update(block)
        if self._is_module:
            # in a module, you return the result of the evaluation
            return result
        else:
            return None

    def handle_emit(self, entry:MappingEntry) -> Node:
        """
        Emits the content of the last stack frame
        (.local + .define/.import blocks),
        excluding non-node types.
        """
        frame = self.stack.peek()
        result = CommentedMap()
        for key in frame:
            if isinstance(frame[key], ALL_NODE_TYPES):
                result[key] = frame[key]
        return result

    # ---------------------
    # Control structures
    # ---------------------
    def handle_do(self, entry:MappingEntry) -> ListNode:
        """
        Sequence of instructions
        (it will also accept a map)

        Collapse a returned sequence:
            - only 1 result, returns it.
            - no result: returns None
        """
        # print(f"*** DO action ***")
        if isinstance(entry.value, (CommentedSeq, list)):
            results = CommentedSeq()
            for node in entry.value:
                r = self.process_node(node)
                if r:
                    results.append(r)
            return collapse_seq(results)
        elif isinstance(entry.value, (CommentedMap, dict)):
            # Accept also a map
            return self.process_node(entry.value)
        else:
            if not isinstance(entry.value, str):
                raise ValueError(f"Unexpected value in entry: {entry.value}")
            return self.evaluate_expression(entry.value)
        

    def handle_foreach(self, entry:MappingEntry) -> Node:
        """
        Loop through a sequence or iterable expression.
        A foreach always returns a sequence.
        This is useful for building composite objects; it's usually what you want.

        .foreach
            .values: [var_name, iterable_expr]: the variable and the list/expression
            .do: [...] : the list of actions
    
        """
        # print("\nFOREACH")
        var_name, iterable_expr = entry[".values"]
        collect_maps = entry.get('.collect_mappings', True)
        # print("foreach expression:", iterable_expr)
        result = self.process_node(iterable_expr)
        # print("foreach result:", type(result).__name__, "=>", result)

        if isinstance(result, Sequence):
            # an iterable
            iterable = result
            results = CommentedSeq()
            for item in iterable:
                local_ctx = {}
                local_ctx[var_name] = item
                self.stack.push(local_ctx)
                # handle the .do block, standardly:
                do_entry = entry.get_sub_entry('.do')
                result = self.handle_do(do_entry)
                results.append(result)
                self.stack.pop()
            if collect_maps:
                # normally we collapse maps
                return collapse_maps(results)
            else:
                return results
        elif isinstance(result, Mapping):
            return result
        else:
            msg = f"Unexpected expression {iterable_expr} ({result}): it returned a {type(result).__name__} instead of a sequence (or map)."
            self.raise_error(entry.value, Error.EXPRESSION, msg)


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


    # ---------------------
    # File management
    # ---------------------

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
        CALLING_FILENAME = self.stack['__SOURCE_FILE__']
        if isinstance(entry.value, str):
            filename = self.evaluate_expression(entry.value)
            format = None
            kwargs = {}
        
        else:
            filename = self.evaluate_expression(entry['.filename'])
            format = entry.get('.format') # get the export format, if there 
            kwargs = entry.get('.args') or {} # arguments
        
        # assign new file
        self.stack['__SOURCE_FILE__'] = filename
        try:
            full_filename = safe_path(self.source_dir, filename)
        except FileNotFoundError as e:
            self.raise_error(entry.value, Error.FILE, e)  
        actual_format = get_format(filename, format)
        with open(full_filename, 'r') as f:
            text = f.read()
        # read the file
        data = deserialize(text, actual_format, **kwargs)
        # _, data = load_yaml(full_filename)
        r = self.process_node(data)
        # reassign the source_file
        self.stack['__SOURCE_FILE__'] = CALLING_FILENAME
        return r

    def handle_export(self, entry: MappingEntry) -> None:
        """
        Exports the subtree into an external file

        export:
            .filename: ...,
            .format: ...  # optional
            .args: { }    # the additional arguments
            .comment: ... # a comment (single or multiple line) that will set at the top
            .do: {...} or []
        """
        filename = self.evaluate_expression(entry['.filename'])
        full_filename = get_full_filename(self.source_dir, filename)
        Path(full_filename).parent.mkdir(parents=True, exist_ok=True)

        format = entry.get('.format')  # get the export format, if there
        kwargs = entry.get('.args') or {}  # arguments
        comment = self.evaluate_expression(entry.get('.comment'))
        tree = self.process_node(entry['.do'])

        # work out the actual format, and export
        actual_format = get_format(filename, format)
        file_output = serialize(tree, actual_format, comment=comment, **kwargs)

        with open(full_filename, 'w') as f:
            f.write(file_output)
        assert Path(full_filename).is_file()
        # print(f"Exported to: {full_filename} ✅ ")

    # ---------------------
    # Programmability and functions
    # ---------------------

    def handle_import(self, entry:MappingEntry) -> None:
        """
        Import a YAMLpp module (it is YAML, by convention), so that
        its content can be accessed from the Jinja interpreter.

        The module is fully separate (separation of concerns).
        NOTE: .import does not load anything on the tree.

        If no items are exposed to the caller's interpreter, 
        then the module's name is exposed,
        and the items within it must be accessed with the dot notation
        (`module.foo`). 

        short form:
        -----------
        .import path/to/my/module.ypp

        The module is executed with the name;
        and its content is accessible on the stack under the name `module`.

        long form:
        -----------
        .import:
            .filename: path/to/my/module.ypp
            .as: my_module # alias
            .exposes: [..., ...] # list of items exposed
        """

        if isinstance(entry.value, str):
            # simple form
            filename = self.evaluate_expression(entry.value)
            module_name = extract_identifier(filename)
            exposes_names = []
        else:
            # long form
            filename = self.evaluate_expression(entry['.filename'])
            module_name = self.evaluate_expression(entry.get('.as')) or extract_identifier(filename)
            exposes_names = entry.get('.exposes', []) 
            if not isinstance(exposes_names,list):
                self.raise_error(entry, Error.ARGUMENTS, f".exposes expects a list (is {type(exposes_names).__name__})")

        
        # load the file
        try:
            full_filename = safe_path(self.source_dir, filename)
        except FileNotFoundError as e:
            self.raise_error(entry, Error.FILE, e)  
        
        # At this point we need to create a new interpreter, with that context
        # print(f"Importing module '{module_name}' from file '{filename}' (full path: '{full_filename}')")    
        i = Interpreter(filename=full_filename, source_dir=self.source_dir, 
                        render=True, is_module=True)
        # module is set to True, so now the functions are stored as plain objects
    
        last_frame = i.stack.top()
        if not exposes_names:
            # no names exposed:
            self.stack[module_name] = last_frame
            return None
        # print("Full tree:", i.tree)
        for item_name in exposes_names:
            # register each exposed item under its name
            try:
                # print(f"Importing item '{item_name}' from module '{module_name}'")  
                item = last_frame[item_name]
            except KeyError:
                # print(f"Stack (for error on item '{item_name}'):", i.stack)
                self.raise_error(entry, Error.ARGUMENTS, 
                                 f"Cannot import item '{item_name}' from module '{module_name}' ('{filename}')")
            # insert into the stack
            self.stack[item_name] = item
        return None
        


                


    def handle_import_module(self, entry:MappingEntry) -> None:
        """
        Import a Python module, with variables (function) and filters.
        The import is scoped.
        """
        filename =  self.evaluate_expression(entry.value)
        try:
            full_filename = safe_path(self.source_dir, filename)
        except FileNotFoundError as e:
            self.raise_error(entry.value, Error.FILE, e)  
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

        This captures the context.

        .function:
            .name: "",
            .args": [...], # sequence 
            .do": [...]
        """
        name = entry['.name']
        # checks:
        entry['.do']
        formal_args = entry['.args']
        if not isinstance(formal_args, list):
            self.raise_error(entry, Error.TYPE, 
                              f"Function {name}'s formal args must be a sequence (is {type(formal_args).__name__})")
        function_context = {".function": entry.value, ".capture": self.stack.capture}
        # insert on stack
        self.stack[name] = function_context
        # print(f"Saved context for function '{name}':", function_context, file=sys.stderr)
        if self._is_module:
            # The function must also be put into the tree, so that it can be exported
            return {name: function_context}
        else:
            return None

        
        

    def handle_call(self, entry:MappingEntry) -> Node:
        """
        Call a function, with its arguments

        .call
            .name: "",
            .args": [...]
        """
        name = entry['.name']
        # print(f"*** CALLING {name} ***")
        try:
            function_context = MappingEntry(name, self.stack[name])
        except KeyError:
            self.raise_error(entry, Error.KEY, f"Function '{name}' not found!")
        
        function = function_context['.function']
        capture  = function_context['.capture']
        
        # assign the arguments
        formal_args = function['.args']
        args = entry['.args']
        # evaluate each argument:
        
        # do not evaluate at this stage.
        if isinstance(args, list):
            # print("args:", args)
            if len(args) != len(formal_args):
                self.raise_error(entry, 
                                Error.ARGUMENTS,
                                f"No of arguments not matching, expected {len(formal_args)}, found {len(args)}")
            assigned_args = dict(zip(formal_args, args))
            # print("Assigned:", assigned_args)
        elif isinstance(args, dict):
            if set(args) != set(formal_args):
                diff = set(args) ^ set(formal_args)
                self.raise_error(entry,
                                  Error.ARGUMENTS,
                                  f"Arguments not matching, differences: {diff}")
            assigned_args = args
        else:
            raise TypeError(f"The argument provided '{args}' is not a map/sequence but a { type(args).__name__}")       

        # create the new block and copy the arguments as context
        actions = function['.do']
        if isinstance(actions, str):
            new_block = actions
        else:
            new_block = actions.copy()
        if isinstance(new_block, (CommentedSeq, list)):
            # normal list (or even a plain string), you need to create a dictionary
            new_block = {'.local': assigned_args, '.do': new_block}
        elif isinstance(new_block, str):
            # str
            new_block = {'.local': assigned_args, '.do': new_block}
        elif isinstance(new_block, (CommentedMap, dict)):
            # a simple dict
            new_block['.local'] = assigned_args
            new_block.move_to_end('.local', last=False) # brigng first
        else:
            raise TypeError("Invalid .do block")

        # Old procedure
        # r = self.process_node(new_block)
        #  if isinstance(r, (list, CommentedSeq)):
        #    r = collapse_seq(r)
        #    print(r)
        # return r

        # At this point we need to create a new interpreter, with that context
        i = Interpreter(source_dir=self.source_dir)
        assert i.source_dir, "The source dir was not correctly assigned"
        i.load_tree(new_block)
        i.stack.push(capture)
        return i.render_tree()



    # ---------------------
    # SQL input
    # ---------------------

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
        except (SQLOperationalError, RuntimeError) as e:
            self.raise_error(entry.value, Error.SQL, e)     
        return rows

    def handle_exec_sql(self, entry:MappingEntry) -> None:
        """
        Execute a query on an connection (SQL Alchemy)

        .exec_sql:
            .engine: ... # the name of the engine
            .query:  ... # the query to be executed
        """
        self._sql_query(entry)
        

    def handle_load_sql(self, entry:MappingEntry) -> ListNode:
        """
        Loads data from an SQL connection (SQL Alchemy) as a sequence

        .load_sql:
            .engine: ... # the name of the engine
            .query:  ... # the query to be executed
        """
        rows = self._sql_query(entry)
        # print("Load SQL was run:\n", rows)
        seq = CommentedSeq()
        for row in rows:
            # Ensure each row is a YAML node, not a plain dict
            seq.append(CommentedMap(row))
        return collapse_seq(seq)



    # ---------------------
    # Buffer generation
    # ---------------------
    def handle_open_buffer(self, entry:MappingEntry) -> None:
        """
        Open a text buffer for output

        .open_buffer:
            .name: ...     # identifier of the buffer
            .language: ... # language (optional, indicative)
            .init:  ...    # initial text
            .indent: ....  # the indentation (default = 4)
        """
        DEFAULT_INDENT = 4
        name = self.evaluate_expression(entry['.name'])
        try:
            check_name(name)
        except Exception as e:
            self.raise_error(entry.value, Error.VALUE, e)
        language = self.evaluate_expression(entry.get('.language'))
        init = self.evaluate_expression(entry.get('.init'))
        indent = self.evaluate_expression(entry.get('.indent', DEFAULT_INDENT))
        self.stack[name] = {'name': name, 
                            'language': language, 
                            'content': [init], # list of items
                            'indent_level': 0,
                            'indent': indent,
                            }

    def handle_write_buffer(self, entry:MappingEntry) -> None:
        """
        Write text into a pre-defined buffer

        The text given as input is evaluated (use %raw/%end_raw to exclude evalution)
        .write_buffer:
            .name: ... # identifier of the buffer
            .align: ... # alignment ('same', 'indent', 'dedent', 'left'; default is 'same')
            .text: ... # text of the buffer
        """
        name = self.evaluate_expression(entry['.name'])
        check_name(name)
        text = self.evaluate_expression(entry.get('.text', ''))
        indent = self.evaluate_expression(entry.get('.indent', 0))
        # update the content buffer:
        content = self.stack[name]['content']
        content.append(Indentation(indent))
        content.append(text)

    def handle_save_buffer(self, entry: MappingEntry) -> None:
        """
        Save the buffer's text in a file.

        .save_buffer:
            .name: ...     # identifier of the buffer
            .filename: ... # filename, relative 
        """
        name = self.evaluate_expression(entry['.name'])
        check_name(name)
        filename = self.evaluate_expression(entry['.filename'])
        if not self.source_dir:
            self.raise_error(entry.value, Error.FILE, "Cannot save, this interpreter has no default dir.")
        full_filename = get_full_filename(self.source_dir, filename)
        assert full_filename
        # print("Full filename:", full_filename)
        # Create and print the output:
        buffer = self.stack[name]
        indent_width = buffer['indent']
        assert indent_width
        file_output = render_buffer(buffer["content"], indent_width)
        with open(full_filename, 'w') as f:
            f.write(file_output)
        assert Path(full_filename).is_file()



    # -------------------------
    # Output
    # -------------------------
        
    @property
    def yaml(self) -> str:
        """
        Return the final YAML output
        (it supports a round trip)
        """
        tree = self.render_tree()
        return to_yaml(tree)

    
    
    def dumps(self, format:str) -> str:
        "Serialize the output into one of the supported serialization formats"
        tree = self.render_tree()
        return serialize(tree, format)
    

    def print(self, filename:str=None) -> str:
        """
        Nicely prints the final YAML output to the console.
        """
        filename = filename or self.source_file
        print_yaml(self.yaml, filename)




def yamlpp_comp(program: str, working_dir: str | None = None) -> tuple[str, Node]:
    """
    Compile and execute a YAMLpp program.

    Parameters
    ----------
    program : str
        The YAMLpp source text to compile and evaluate.
    working_dir : str | None
        The directory used as the base for relative file operations
        during compilation and evaluation.

    Returns
    -------
    output_yaml :
        The final YAML output produced by the interpreter,
        serialized as a YAML-formatted string. This is the fully
        evaluated result of the program (not the original source).
    tree :
        The internal AST representation of the evaluated result.
        This is a structured, in-memory data model corresponding
        to the final YAML output (it is *not* the source AST, but
        the tree after evaluation).
    """

    i = Interpreter(source_dir=working_dir)
    i.load_text(program)
    return i.yaml, i.tree