# Language reference

## Glossary

_Terms in the definitions that are defined in this glossary are preceded by an arrow (➙)._

### General

- **Protein**: A language based on ➙ YAML,
  which ➙ pre-processes a ➙ tree containing ➙ constructs into a plain YAML tree.

- **YAML™**: A data serialization language used in modern computer programs, mainly
  for configuration files that are complex and nested, and as a foundation for domain-specific languages (see [Official definition](https://yaml.org/spec/))

- **Pre-process**: To transform high-level data into a plainer form that will be processed. 

### YAML

- **Tree**: In YAML, a structure made of a node that can point to one or more nodes, and so on.

- **Node**: In YAML, a fundamental unit of data; it can be a ➙ scalar, ➙ sequence or ➙ mapping.
  In Protein, it can also be an ➙ expression.

- **Scalar**: in YAML, a "leaf" in a YAML tree: it can be a numeric value, a string, or a boolean.

- **Sequence**: In YAML, an ordered collection of objects (➙ a list in Python).

- **Mapping**: In YAML, an ordered collection of ➙ key, ➙ value pairs (➙ a dictionary in Python).

- **Key**: In YAML, a string that identifies a ➙ value in a map.

- **Value**: In YAML, a ➙ node associated to a ➙ key.

- **Block** A piece of YAML code containing a ➙ sequence or ➙ mapping, 
  with the  ➙ key on the first line, and the content (node) indented in the following lines. 

### Protein

- **Keyword**: A YAML ➙ key preceded by a dot (`.`), which has a meaning in the context of Protein.

- **Construct**: An instruction of Protein ➙ pre-processing instructions that generates
  one or more YAML ➙ nodes. <br>
  All constructs are valid YAML.<br>
  Each construct has a ➙ keyword starting with a dot (`.`) and is presented as a ➙ block. <br>
  It is called a construct because it _constructs_ (builds) one or more nodes.
  

- **Expression**: A string ➙ value containing an expression, which returns a node.
   An expression is written in the ➙ Jinja language.  

- **Expand / Render**: To evaluate a ➙ Jinja expression and return a ➙ node.

- **Jinja**: The templating engine that is used to calculate ➙ values in Protein (see [documentation](https://jinja.palletsprojects.com/)).

- **Module**: An imported piece of Python code (file or package) that provides variables, 
  ➙ Python functions and [filters](https://jinja.palletsprojects.com/en/stable/templates/#filters) to the ➙ Jinja environment, for evaluating ➙ expressions.

- **Python Function**: a function (in the sense of the language Python) that can be used in
  ➙ expressions.
  

- **Frame**: a mapping of variables and functions, to be used
  by Protein when evaluating Jinja expressions.

- **Frame Stack**: the dynamically generated stack of all ➙ frames currently active. The stack is _not_ dependent on the structure of the data tree; it is built by explicit ➙ constructs found on that tree, such as importing a ➙ module, or creating a new ➙ frame.
In other words, if none of these constructs are found in a
tree, the frame stack remains the same (all variables are stored in that frame).

- **Variable**: an item stored a frame;
  it has a name (➙ key) and a ➙ value. A variable can be a ➙ scalar, ➙ a mapping, ➙ a sequence,
  a Protein ➙ function, or a ➙ Python function.

- **(Lexical) Scope**: the filter saying which variables the
  Protein program currently
  has access to. The rules for the scope are simple: look for at the variable in the top frame of the stack,
  and if not found, look for it in
  the next frame down, and so on, until the bottom the frame stack.
  The term **lexical** refers to "the rules that decide where a name
  exists and how it can be accessed".

- **Function**: in Protein's terminology, it is a variable that
  refers to a sequence of Protein constructs, with specified
  arguments. A function is computed only when it is called.

- **Context**: the projection (snapshot) of the frame stack
  at a specific moment, showing all variables visible in the
  current scope. When a ➙ function is created, it also captures its 
  own ➙ context, so that this function can be called later in
  a predictable way (with the variables having the exact same meaning
  they had when the function was declared). A context
  is static, i.e. a change of a variable's value at a later moment
  does not change the context as it was captured.




## General principles

1. All language constructs start with keywords (valid YAML keys, prefixed with the symbol **`.`**).
They "run, transform the tree and disappear".
1. All other key/values in the source file are plain YAML.
2. Internally, all values (nodes) are:
      - **Maps** (dictionaries)
      - **Sequences** (lists)
      - **Scalars**: 
        - integers, 
        - reals, 
        - strings,
        - booleans (`true`, `false`), 
        - timestamps ([ISO-8601](https://www.cl.cam.ac.uk/~mgk25/iso-time.html)), and
        - `null` 
3. A **string** value can be a [Jinja statement](https://jinja.palletsprojects.com/en/stable/).
      - That expression relies in particular on variables.
      - Jinja always returns a string.
      - If the result string is a valid Python literal (a scalar, or a list or a dictionary), then **Protein will automatically convert it into a node** [^a]
4. A Protein value collapses results of sequences (lists), in a way that is natural
   for the purpose 
   (empty lists return nothing, a list of 1 returns the item, etc.).
   For more details, see [description](advanced.md#collapse-rule)
5. Keys can also contain Jinja2 statements (you can write `{server_name}: ...` 
   instead of `production: ...`, as long as `server_name` is a defined variable.
6. The final output is a YAML tree where all Protein constructs have disappeared.

[^a]: This conversion is made with the function [`ast.literal_eval()`](https://docs.python.org/3/library/ast.html#ast.literal_eval).

!!!Tip "Protein obeys the rules of YAML syntax"
    - It provides declarative constructs without breaking YAML syntax. 
    - It allows modular, reusable, and expressive constructs that generate YAML files.




## 🔧 Constructs of the Protein language

Each construct is defined below with its purpose and an example.

### Printing

#### `.print`
**Definition**: Printing a line to the console.

!!! Note "Output to stderr"
    It goes to the stderr file, to keep it distinct from the output,
    in case the output (YAML) is sent to the console.

**Example**:

```yaml
.print "Hello World"
```

### Variables

#### `.define`
**Definition**: A construct that adds variables to the *current* scope.

You can insert a `.define` block at any node of the tree.

!!! Important
    `.define` is the default construct you use to define variables.



**Example**:
```yaml
.define:
  greeting: "Hello"
  name: "Alice"

message: "{{ greeting }}, {{ name }}!"
```

**Output**:
```yaml
message: "Hello, Alice!"
```


#### `.local`
**Definition**: Creates a new **scope** for variables or functions.

In that new scope, the variables and functions already created
are still visible. However, the new ones that you create
will remain **local** to that part of the tree. 
They do not influence the rest of the tree.
Once the interpreter will have finished walking that
part of the tree, the scope will die.

You can define a `.local` block at any node of the tree.

You can define variables directly within a `.local` construct,
without having to use an additional `.define` construct.

!!! Warning "Scope of the definitions"
    The variables defined here have a **lexical scope**: they are visible to all sibling nodes 
    in the tree and their descendants,  
    but **not** to any part of the tree *above* the `.local` block.

!!! Note "Implementation Note"
    What the `.local` construct does, under the hood,
    is that it pushes a new frame on the the frame stack
    (which contains the variables, functions and Python functions).
    When the sequence or mapping in which the `.local` construct is found
    ends, the frame is removed.



**Example**:
```yaml
new:
  .local:
    greeting: "Hello"
    name: "Alice"

  message: "{{ greeting }}, {{ name }}!"

outside:
 # Here the variables `greeting` and `name` are not visible 
```

**Output**:
```yaml
new:
  message: "Hello, Alice!"

outside:
```






### Control structures

#### `.do`
**Definition**: Execute a sequence of node creations, in order. 

In principle, it returns a list, unless:

- that list is of length 1, in which case it returns a scalar.
- that list is empty, in which case it returns `null`

This is called **[collapse](advanced.md#the-collapse-rule))**.

However, if `.do` precedes a map, it will process and return it.


**Example**:
```yaml
.do:
  - step: "Initialize"
  - step: "Run process"
  - step: "Finalize"
```
**Output**:
```yaml
- step: "Initialize"
- step: "Run process"
- step: "Finalize"
```

#### `.if`
**Definition**: Create a YAML node, according to condition, with then and else.  
**Example**:
```yaml
.if:
  .cond: "{{ value > 10 }}"
  .then:
    result: "Large"
  .else:
    result: "Small"
```

If `value = 12` →  
```yaml
result: "Large"
```

#### `.foreach`
**Definition**: Iterates over values with a loop body. 
If you iterate over a sequence, you will **always** get a sequence (even if empty or with length of 1).

However, if the expression results in a map, `.foreach` just returns the map. 

**Example**:
```yaml
.local:
  items: [1, 2, 3]

.foreach:
  .values: [x, items]
  .do:
    - square: "{{ x * x }}"
```
**Output**:
```yaml
- square: 1
- square: 4
- square: 9
```



#### `.switch`
**Definition**: Branch to create a different YAML node, based on an expression and cases.  
**Example**:
```yaml
.switch:
  .expr: "{{ color }}"
  .cases:
    red:
      meaning: "Stop"
    green:
      meaning: "Go"
  .default:
    meaning: "Unknown"
```
If `color = "green"` →  
```yaml
meaning: "Go"
```

#### `.exit`
**Definition**: Terminate the execution, with a message and an optional exit code (default: 0).
It raises the exception ProteinExitError; the CLI terminates with the exit code.

**Form**:
```yaml
.exit:
  .code: <integer>        # optional
  .message: <string>      # required
```

**Example**:
```yaml
.exit:
  .code: 2
  .message: "Invalid configuration"
```



### File Management


#### `.load`
**Definition**: Insert and preprocesses another Protein (or YAML) file, at this place in the tree.  
**Example**:
```yaml
.load: "other.yaml"
```

This loads, the contents of `other.yaml` into the current document,
and loads it at the place of the .load statement.

Complete form:

```yaml
.load:
  .filename: "other.yaml"
  .format:
  .args: # arguments are by name
    ...

```

- The file extension (`yaml`, `json`, `toml`...) is optional.
- The `.format` keyword is optional.
- The `.args` keyword is used for the additional arguments passed to the format-specific 
  load function (by name).


#### `.export`
**Definition**: Export the current portion of the tree into an external file. The tree is
normalized, in the sense that

- it is turned into a pure tree (references to anchors are replaced by the actual node)
- all types are: dict, list, str, int, float and bool.

**Example**:
```yaml
.export:
  .filename: "export/foo.yaml"
  .format: yaml          # optional
  .args:    
    indent: 4            # control indentation width
  .comment: ...           # an optional message
  .do: ...               # the part you wish to export.
```

The exported file can be either plain YAML or other format. 
Protein constructs are expanded into YAML, before being exported.

- The file extension (`yaml`, `json`, `toml`...) is optional.
- The `.format` keyword is optional.
- The `.args` keyword is used for the additional arguments passed to the format-specific 
  export function (by name).
- The `.comment` keyword is used to issue a comment (could be multiline) at the top of the file
  for the formats that accept it (all but json).
  If no comment is given, a standard comment is added (to indicate that the file was auto-generated).


=== "JSON, TOML and others"

    | Format     | Library / Function          | Implicit Argument(tree)            | Optional Arguments                                                                                               | Documentation                                                               |
    | ---------- | --------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
    | **json**   | `json.dumps(obj, **kwargs)` | `obj` (serializable Python object) | `skipkeys`, `ensure_ascii`, `check_circular`, `allow_nan`, `indent`, `separators`, `default`, `sort_keys`, `cls` | [Python json docs](https://docs.python.org/3/library/json.html#json.dumps)  |
    | **toml**   | `tomlkit.dumps(data)`       | `data` (dict or TOMLDocument)      | None — intentionally minimal, style‑preserving only                                                              | [tomlkit docs](https://tomlkit.readthedocs.io/en/latest/api/#tomlkit.dumps) |
    | **python** | `repr`                      | expression                         | —                                                                                                                | [Python docs](https://docs.python.org/3/library/functions.html#repr)        |


=== "YAML"


    !!! Tip "Reason why"  
        The reason why the tool had to implement its own export argument specification, is that
        [Ruamel](https://yaml.dev/doc/ruamel.yaml/) does not offer a simple,
        data-driven way of specifying the output
        (instead would have to use methods to set each parameter).




    This is the table of arguments for the `yaml` format:

    | Argument          | Description                                         | Values                         | Default Value (ruamel.yaml) | Output                             |
    | ----------------- | --------------------------------------------------- | ------------------------------ | --------------------------- | ---------------------------------- |
    | `indent`          | Spaces for nested mappings and sequences            | Integer ≥ 1                    | 2                           | Controls block indentation depth   |
    | `offset`          | Spaces between sequence dash (`-`) and item content | Integer ≥ 0                    | 2                           | Affects alignment of list items    |
    | `explicit_start`  | Emit `---` at start of document                     | True / False                   | False                       | Adds YAML document start marker    |
    | `explicit_end`    | Emit `...` at end of document                       | True / False                   | False                       | Adds YAML document end marker      |
    | `allow_unicode`   | Permit non‑ASCII characters                         | True / False                   | True                        | Controls escaping of Unicode       |
    | `canonical`       | Emit canonical form (explicit scalars, sorted keys) | True / False                   | False                       | Produces strict, verbose YAML      |
    | `width`           | Preferred line width before wrapping                | Integer ≥ 0                    | 80                          | Controls line breaks in scalars    |
    | `preserve_quotes` | Keep original quoting style when round‑tripping     | True / False                   | False                       | Preserves `'` vs `"` in output     |
    | `typ`             | Loader/dumper type                                  | "rt", "safe", "base", "unsafe" | "rt"                        | Determines round‑trip vs safe mode |
    | `pure`            | Use pure Python implementation                      | True / False                   | None (ruamel decides)       | Affects performance, not output    |
    | `version`         | YAML specification version                          | Tuple (major, minor)           | None                        | Adds `%YAML x.y` directive         |


    !!! Warning "Default values"
        Protein is not opinionated at all on the values (Ruamel decides), with one exception:

        - **The default `typ` is 'rt', to ensure round-trip**. 
        - **No duplicate keys are allowed**
          (this is hard-coded, for consistency: the YAML spec explicitly forbids it,
          and a second key would override the earlier one, which could introduce undetected bugs). 



**Output**:
None (the tree is exported to the external file)




### Programmability

#### `.import_module`
**Definition**: Import a Python module, exposing functions and filters to the Jinja expressions.

!!! Note "Delegation to Python"
    In Protein / Protein pipelines, **any complex logic that operates on a single mapping** (dictionary)
    should be implemented as a **function** in Python, inside a module — not inside the Protein code.

    Protein should remain declarative; Python is the better place for computation.


**Example**:
```yaml
.import_module: "module.py"
```

```python
"""
A sample module
"""

from protein import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    @env.export
    def greet(name: str) -> str:
        return f"Hello {name}"
    
    @env.filter
    def shout(value: str) -> str:
        return f"{value.upper()}!!!"
    
    env.variables["app_name"] = "Protein"
```

This makes variables and filters from `module.py` available in Jinja2 expressions.




#### `.function`
**Definition**: Define a reusable function with arguments and a body. Arguments are positional.  
A `.function` construct is declarative; it is stored as‑is (unexecuted) in the context.

**Caution**: These functions are not available “as‑is” inside Jinja expressions.

**Example**:
```yaml
.function:
  .name: "greet"
  .args: ["name"]
  .do:
    - message: "Hello {{ name }}!"
```



#### `.call`
**Definition**: Invoke a previously defined `.function` construct, with arguments.

This is the moment when the `.function` body is executed.  
Execution happens within the context **as it existed at the time the `.function` was defined**,  
as if the body had been executed at that moment.

A `.call` creates a temporary execution context (a new frame).  
This frame contains:

- the captured environment (closure)  
- the function arguments  
- any inner declarations  

The frame is destroyed immediately after the function returns.

Because of this model, an inner function can be called *from within* its enclosing function,  
but it is **never visible to the caller** outside that function’s lexical scope.

Calls can be done by position (sequence) or by name (mapping), but not a mix of the two.

**Example**:
```yaml
.call:
  .name: "greet"
  .args: ["Alice"]
```

or 

```yaml
.call:
  .name: "greet"
  .args:
    name: "Alice"
```

**Output**:
```yaml
message: "Hello Alice!"
```





### Loading from SQL tables

It can be useful to load values from an SQL table.
Protein uses SQLAlchemy as the underlying tool.

Below is a clean, minimal, **reference‑style** documentation block for the three directives, written in the Protein operational dialect you and I have been stabilizing. No Python, no narrative—just the contract.



#### `.def_sql`

**Purpose:**  
Declare and register an SQLAlchemy engine under a symbolic name.

**Specification:**  
```
def_sql:
  .name: <engine-name>     # identifier used later
  .url:  <SQLAlchemy-URL>  # dialect+driver+location string
  .args: <mapping?>        # optional keyword arguments
```

**Reference:**  
[SQLAlchemy Engine Creation](https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine)



**Example**
```yaml
def_sql:
  .name: main_db
  .url: "sqlite:///./data.db"
  .args:
    echo: false
    future: true
```



#### `.exec_sql`

**Purpose:**  
Execute an SQL query on a previously declared engine.  
Used for statements where the result is not consumed (e.g., INSERT, UPDATE, DDL).

**Specification:**  
```
exec_sql:
  .engine: <engine-name>   # name defined via def_sql
  .query:  <query-object>  # structure understood by sql_query()
```



**Example**
```yaml
exec_sql:
  .engine: main_db
  .query:
    text: |
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER
      )
```

or

```yaml
exec_sql:
  .engine: main_db
  .query:
    text: |
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER
      )
```




#### `.load_sql`

**Purpose:**  
Execute an SQL query and return the resulting rows as a YAML sequence of mappings.

**Specification:**  
```
load_sql:
  .engine: <engine-name>   # name defined via def_sql
  .query:  <query-object>  # structure understood by sql_query()
```




**Example**
```yaml
load_sql:
  .engine: main_db
  .query:
    text: "SELECT id, name, age FROM users ORDER BY id"
```

**Output:**
A YAML sequence of mapping nodes, one per row.

```yaml
- id: 1
  name: Alice
  age: 30
- id: 2
  name: Bob
  age: 41
```

### File Generation (non-structured)

#### `.write`

**Definition**: Write directly into a text file (non-structured).
The location of the file is relative to the source directory of the program.
It has two argumnents: `filename` and `text`.

**Example**:

```yaml
.write:
    .filename: myfile.txt
    .text: |
        Hello World
```

### Buffer generation

These instructs are used to create text-based output files.

They are especially suited for formats (such as HTML) that do not require indentation.

!!! Warning "Do not use to produce structured outputs"
    For formats such as YAML, JSON, dotenv, etc., use instead the `.export` construct.


#### `.open_buffer`

**Definition**: Declare and initialize a named text buffer.  
A buffer is a logical container that will later receive text fragments and be saved to a file.

**Fields**:

| Field       | Required | Description                                            |
| ----------- | -------- | ------------------------------------------------------ |
| `.name`     | yes      | Identifier of the buffer. Must be a valid buffer name. |
| `.language` | no       | Indicative language tag (informational only).          |
| `.init`     | no       | Initial text placed in the buffer.                     |
| `.indent`   | no       | Base indentation width (in spaces). Default: `4`.      |

**Example**:
```yaml
.open_buffer:
  .name: "main"
  .language: "python"
  .init: "# Generated file"
  .indent: 2
```



#### `.write_buffer`

**Definition**: Append text to an existing buffer.  

The `.text` field is evaluated (unless wrapped in `%raw` / `%end_raw`).

**Fields**:

| Field     | Required | Description                                                                                 |
| --------- | -------- | ------------------------------------------------------------------------------------------- |
| `.name`   | yes      | Identifier of the buffer to write into.                                                     |
| `.text`   | no       | Text to append (evaluated). Default: empty string.                                          |
| `.indent` | no       | Relative indentation adjustment for this fragment (in units, not spaces). <br>Default: `0`. |

**Additional Information**:

By default the text is always left-aligned to the previous line; this is generally what you want.

If needed, use an `.indent` number (positive or negative number of indentations) to recalibrate where
your line should be left-aligned.

**Example**:
```yaml
.write_buffer:
  .name: "main"
  .indent: 1
  .text: "print('Hello')"
```



#### `.save_buffer`

**Definition**: Write the contents of a buffer to a file.

The location of the file is relative to the source directory of the program.

**Fields**:

| Field       | Required | Description                                        |
| ----------- | -------- | -------------------------------------------------- |
| `.name`     | yes      | Identifier of the buffer to save.                  |
| `.filename` | yes      | Output filename, relative to the source directory. |

**Example**:
```yaml
.save_buffer:
  .name: "main"
  .filename: "output.py"
```











