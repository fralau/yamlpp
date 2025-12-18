# Language reference

## Glossary

_Terms in the definitions that are defined in this glossary are preceded by an arrow (➙)._

### General

- **YAMLpp**: A language based on ➙ YAML,
  which ➙ pre-processes a ➙ tree containing ➙ constructs into a plain YAML tree.

- **YAML™**: A data serialization language used in modern computer programs, mainly
  for configuration files that are complex and nested, and as a foundation for domain-specific languages (see [Official definition](https://yaml.org/spec/))

- **Pre-process**: To transform high-level data into a plainer form that will be processed. 

### YAML

- **Tree**: In YAML, a structure made of a node that can point to one or more nodes, and so on.

- **Node**: In YAML, a fundamental unit of data; it can be a ➙ scalar, ➙ sequence or ➙ mapping.
  In YAMLpp, it can also be an ➙ expression.

- **Scalar**: in YAML, a "leaf" in a YAML tree: it can be a numeric value, a string, or a boolean.

- **Sequence**: In YAML, an ordered collection of objects (➙ a list in Python).

- **Mapping**: In YAML, an ordered collection of ➙ key, ➙ value pairs (➙ a dictionary in Python).

- **Key**: In YAML, a string that identifies a ➙ value in a map.

- **Value**: In YAML, a ➙ node associated to a ➙ key.

- **Block** A piece of YAML code containing a ➙ sequence or ➙ mapping, 
  with the  ➙ key on the first line, and the content (node) indented in the following lines. 

### YAMLpp


- **Keyword**: A YAML ➙ key preceded by a dot (`.`), which has a meaning in the context of YAMLpp.

- **Construct**: An instruction of YAMLpp ➙ pre-processing instructions that generates
  one or more YAML ➙ nodes. <br>
  All constructs are valid YAML.<br>
  Each construct has a ➙ keyword starting with a dot (`.`) and is presented as a ➙ block. <br>
  It is called a construct because it _constructs_ (builds) one or more nodes.
  

- **Expression**: A string ➙ value containing an expression, which returns a node.
   An expression is written in the ➙ Jinja language.  

- **Expand / Render**: To evaluate a ➙ Jinja expression and return a ➙ node.

- **Jinja**: The templating engine that is used to calculate ➙ values in YAMLpp (see [documentation](https://jinja.palletsprojects.com/)).

- **Module**: An imported piece of Python code (file or package) that provides variables, functions and [filters](https://jinja.palletsprojects.com/en/stable/templates/#filters) to the ➙ Jinja environment.



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
3. A value can be any YAML valid value. 
4. It can also be a string containing a [Jinja statement](https://jinja.palletsprojects.com/en/stable/).
   If the result string is a valid Python literal (a scalar, or a list or dictionary), then YAMLpp will convert it into a node.
5. The final output is a YAML tree where all YAMLpp constructs have disappeared.

!!!Tip "YAMLpp obeys the rules of YAML syntax"
    - It provides declarative constructs without breaking YAML syntax. 
    - It allows modular, reusable, and expressive constructs that generate YAML files.

## 🔧 Constructs

Each construct is defined below with its purpose and an example.

### `.context`
**Definition**: A mapping that defines a local scope of variables.

You can define a `.context` block at any node of the tree.

!!! Warning "Scope of the definitions"
    The variables defined have a **scope**: they are valid for all the sibling nodes and their descendents
    (but are not accessible in any part of the tree that is higher than the `.context` block.)

**Example**:
```yaml
.context:
  greeting: "Hello"
  name: "Alice"

message: "{{ greeting }}, {{ name }}!"
```
**Output**:
```yaml
message: "Hello, Alice!"
```



### `.do`
**Definition**: Execute a sequence of node creations, in order.

However, if it finds a map, it will process and return it.


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



### `.foreach`
**Definition**: Iterates over values with a loop body.
You could also generate a map (dictionary) instead of a sequence (list). 

**Example**:
```yaml
.context:
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



### `.switch`
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



### `.if`
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



### `.load`
**Definition**: Insert and preprocesses another YAMLpp (or YAML) file, at this place in the tree.  
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









### `.function`
**Definition**: Define a reusable function with arguments and a body. Arguments are positional.

**Caution**: These functions are not available "as-is" inside of Jinja expressions.

**Example**:
```yaml
.function:
  .name: "greet"
  .args: ["name"]
  .do:
    - message: "Hello {{ name }}!"
```



### `.call`
**Definition**: Invoke a previously defined function with arguments.  
**Example**:
```yaml
.call:
  .name: "greet"
  .args: ["Alice"]
```
**Output**:
```yaml
message: "Hello Alice!"
```

### `.import`
**Definition**: Import a Python module, exposing functions and filters to the Jinja expressions.
  
**Example**:
```yaml
.import: "module.py"
```

```python
"""
A sample module
"""

from yamlpp import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    @env.export
    def greet(name: str) -> str:
        return f"Hello {name}"
    
    @env.filter
    def shout(value: str) -> str:
        return f"{value.upper()}!!!"
    
    env.variables["app_name"] = "YAMLpp"
```

This makes variables and filters from `module.py` available in Jinja2 expressions.

### `.export`
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
  .do: ...               # the part you wish to export.
```

The exported file can be either plain YAML or other format. 
YAMLpp constructs are expanded into YAML, before being exported.

- The file extension (`yaml`, `json`, `toml`...) is optional.
- The `.format` keyword is optional.
- The `.args` keyword is used for the additional arguments passed to the format-specific 
  export function (by name).


=== "JSON, TOML and others"

    | Format   | Library / Function                  | Implicit Argument(tree)                  | Optional Arguments                                                                 | Documentation |
    |----------|-------------------------------------|------------------------------------------|------------------------------------------------------------------------------------|---------------|
    | **json** | `json.dumps(obj, **kwargs)`         | `obj` (serializable Python object)       | `skipkeys`, `ensure_ascii`, `check_circular`, `allow_nan`, `indent`, `separators`, `default`, `sort_keys`, `cls` | [Python json docs](https://docs.python.org/3/library/json.html#json.dumps) |
    | **toml** | `tomlkit.dumps(data)`               | `data` (dict or TOMLDocument)            | None — intentionally minimal, style‑preserving only                                | [tomlkit docs](https://tomlkit.readthedocs.io/en/latest/api/#tomlkit.dumps) |
    | **python** | `repr`                            | expression                               | —                                                                                  | [Python docs](https://docs.python.org/3/library/functions.html#repr) |


=== "YAML"

    The logic is handled directly by the function `yamlpp.util.to_yaml()`.


    !!! Tip "Reason why"  
        The reason why the tool had to implement its own export argument specification, is that
        [Ruamel](https://yaml.dev/doc/ruamel.yaml/) does not offer a simple,
        data-driven way of specifying the output
        (instead would have to use methods to set each parameter).




    This is the table of arguments for the `yaml` format:

    | Argument             | Description                                                                 | Values                          | Default Value (ruamel.yaml) | Output                 |
    |----------------------|-------------------------------------------------------------------------|------------------------------------------|-----------------------------|-------------------------------------------|
    | `indent`             | Spaces for nested mappings and sequences                                | Integer ≥ 1                              | 2                           | Controls block indentation depth          |
    | `offset`             | Spaces between sequence dash (`-`) and item content                     | Integer ≥ 0                              | 2                           | Affects alignment of list items           |
    | `explicit_start`     | Emit `---` at start of document                                         | True / False                             | False                       | Adds YAML document start marker           |
    | `explicit_end`       | Emit `...` at end of document                                           | True / False                             | False                       | Adds YAML document end marker             |
    | `allow_unicode`      | Permit non‑ASCII characters                                             | True / False                             | True                        | Controls escaping of Unicode              |
    | `canonical`          | Emit canonical form (explicit scalars, sorted keys)                     | True / False                             | False                       | Produces strict, verbose YAML             |
    | `width`              | Preferred line width before wrapping                                    | Integer ≥ 0                              | 80                          | Controls line breaks in scalars           |
    | `preserve_quotes`    | Keep original quoting style when round‑tripping                         | True / False                             | False                       | Preserves `'` vs `"` in output            |
    | `typ`                | Loader/dumper type                                                      | "rt", "safe", "base", "unsafe"           | "rt"                        | Determines round‑trip vs safe mode        |
    | `pure`               | Use pure Python implementation                                          | True / False                             | None (ruamel decides)       | Affects performance, not output           |
    | `version`            | YAML specification version                                              | Tuple (major, minor)                     | None                        | Adds `%YAML x.y` directive                |


    !!! Warning "Default values"
        YAMLpp is not opinionated at all on the values (Ruamel decides), with one exception:

        - **The default `typ` is 'rt', to ensure round-trip**. 
        - **No duplicate keys are allowed**
          (this is hard-coded, for consistency: the YAML spec explicitly forbids it,
          and a second key would override the earlier one, which could introduce undetected bugs). 







**Output**:
None (the tree is exported to the external file)


## Loading from SQL tables

It can be useful to load values from an SQL table.
YAMLpp uses SQLAlchemy as the underlying tool.

Below is a clean, minimal, **reference‑style** documentation block for the three directives, written in the YAMLpp operational dialect you and I have been stabilizing. No Python, no narrative—just the contract.



### `.def_sql`

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
SQLAlchemy Engine Creation  
https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine



**Example**
```yaml
def_sql:
  .name: main_db
  .url: "sqlite:///./data.db"
  .args:
    echo: false
    future: true
```



### `.exec_sql`

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




### `.load_sql`

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









## Dynamically changing the initial context

There are two ways of changing the context of your YAMLpp file.

### From the command line

From the command-line, you can update (or create) the top-level `.create` context
in your initial YAMLpp tree.

```sh
yamlpp test1.yaml --set env=prod count=5
```

Supposing that your YAMLpp file contained:

```yaml
.context
  env: test
  count: 3
  foo: barbaz
```

It will contain:
```yaml
.context
  env: prod
  count: 5
  foo: barbaz
```

If the tree started with a sequence, a top level map will be created:

```yaml
.context
  env: prod
  count: 5
.do
  - ...
```

#### Arguments as sequences or maps
You can also set arguments as sequences or maps (use YAML syntax):

```sh
yamlpp test1.yaml --set env=prod users="[Laurent, Paul]"
```


### Through environment variables

Another way to change dynamically the initial conditions that govern a YAMLpp program,
is to use the environment variables of the OS, through the `getenv()` function.

This statement may be used in any part of the YAMLpp tree.

```yaml
server:
  address: "{{ get_env('MY_SERVER`)}}"
```


