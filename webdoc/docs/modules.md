# Expanding Protein with Protein Modules

## How Modules Work

A Protein module may export Python variables, functions, and filters, which become available inside a Protein program in two complementary ways: 

1. As variables, functions or filters inside expressions (called with `{{ my_function(...) }}` in Jinja). 
1. If they are functions, as new constructs (called with `.my_function:` in YAML) and 

 
!!! Important "Duality of functions"

    This duality is fundamental: every imported Python function can be used both as a **construct**, and
    a **function** within a Jinja expression. 

This chapter explains how modules work, how they interact with scopes, and how to use them effectively.

## Definition and Purpose of a Protein Module

The standard Protein's constructs exist "as themselves". This is the **core** of Protein.

Nevertheless, the Protein interpreter runs on a **host** (the Python environment). 
You can use that host to extend the capabilities of Protein, thanks to **Protein Modules**.

Protein **modules** are wrappers for lists of **variables**, **functions** and **filters** written in Python.

They allow you to enrich Protein with functions that:

- Perform arithmetic operations (string utilities, math helpers, path manipulation, etc.), 
- Give access to external data (files, databases, APIs),
- Provide any reusable logic that you want to share across multiple Protein programs.

A module is a Python file that uses a `define_env(env)` function. Inside this function, you declare what you want to expose.

### Outline

Here is an outline of how to write a Protein module:

```python
from protein import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    "This function contains the exports"

    # export a variable:
    env.variables["foo"] = 42

    # export a function:
    @env.export
    def my_function(...):
        return ...

    # export a Jinja filter:
    @env.filter
    def shout(value: str) -> str:
        return value.upper()
    
```

Once imported into your Protein program, the module’s exports become part of the current scope and can be used anywhere within that scope.

!!! Warning "Do not confuse a Protein module with a Python package!"
    A **Protein module** is **not** any type of Python package. 
    It is a Python program, but written in a very exact way,
    to define explicitly which variables, functions and filters
    you want to export.

    If you attempt to import a "normal" Python package, **it will not work**!


### Filters
A **filter** is a special function in Jinja behind a `|` symbol; its first argument is the string that precedes it. 

The filter `shout` can then be used in this way:

```yaml
foo = "{{ 'Hello World' | shout }}"
```

The string `Hello World` is the argument of the function `shout`.

To know more about filters, see the [description in the Jinja documentation](https://jinja.palletsprojects.com/en/stable/api/#custom-filters).

### Decorators
The idioms `@env.export` and `@env.filter` are called **decorators**.
They mark the functions you want to export as functions and filters, respectively. 


You could write the module in the following way:

```python
def my_function(...):
    return ...

def shout(value: str) -> str:
    return value.upper()

def define_env(env: ModuleEnvironment):
    "This function contains the exports"

    env.variables["my_function"] = my_function

    env.filters["shout"] = shout
```

This is equivalent to using the decorators.





## Calling exported functions
### As constructs
Any exported function can be invoked as a construct:

if the function had been define in Python as:

```Python
def define_env(env: ModuleEnvironment):
    "This function contains the exports"

    @env.export
    def my_function(arg1:str, arg2:str):
        return ...
```

Then it could be used in this way (arguments called by position):

```yaml
.my_function: [foo, bar]
```
or (arguments called by name):

```yaml
.my_function:
  arg1: foo
  arg2: bar
```





Protein evaluates the arguments, calls the Python function, and replaces the construct with the return value. This is ideal for structural transformations, data loading, or producing YAML/JSON fragments.

### Inside expressions
The same function can also be used inside expressions:
```yaml
value: "{{ my_function('foo', 'bar') }}"
```
This is ideal for computing values, formatting strings, or performing small transformations. One export gives you both call paths automatically.

## Scoping rules
Protein maintains a stack of scopes. A program begins with its own scope, and additional scopes may be created by constructs such as `.local`. When resolving a variable or function name, Protein searches the current scope, then underlying scopes, then host bindings (exported module values). Modules populate the current scope with exported variables, exported functions, and exported filters.

## Host bindings
`.define` stores variables in the current scope. `.function` stores Protein-defined functions in the current scope. When you import a module:
```yaml
.import_module: path/to/module.py
```
Protein executes the module’s `define_env()` function and adds its exports to the current scope. These exports become available as constructs, as expression-level callables, and as filters (if declared as filters).


### Export types
| Export type          | Construct         | Expression                 | Filter        |
| -------------------- | ----------------- | -------------------------- | ------------- |
| `@env.export`        | ✔️ `.my_function:` | ✔️ `{{ my_function(...) }}` | ❌             |
| `@env.filter`        | ❌                 | ✔️ `{{ value                | my_filter }}` | ✔️ |
| `env.variables[...]` | ✔️ `.varname`      | ✔️ `{{ varname }}`          | ❌             |

## Results of functions  (aside of strings)

Most of the time, you would think of a function as something returning a **string** to Protein.
However, this is **not** always the case.

Functions or filters your write **may** return the following values:

- **Scalars**: strings, reals, integers, booleans
- **Mappings**: these are essentially dictionaries, or compatible types
- **Sequences**: these are essentially lists, or compatible types.

!!! Warning "Exported Functions are not allowed to return any other types"
    The returned values from functions you write in Protein modules, are tested
    at runtime. If a value of any other type than the above is found, Protein will raise a TYPERROR.

Supposing that you had the following function:

```python
    # export a function:
    @env.export
    def my_function():
        return ['foo', 'bar', 'baz']
```

Then: 

```yaml
foo:
    .my_function: []
```

Would return:
```yaml
foo:
    - foo
    - bar
    - baz
```

If you use the second form (with Jinja):

```yaml
foo: "{{ my_function() }}"
```

**you will obtain the same result**:

```yaml
foo:
    - foo
    - bar
    - baz
```

!!! question "How is this possible?"

    We now that Jinja expressions return only strings; so how it possible that
    a value from expression is could be transformed into sequences, mappings, etc.?
    
    The answer is simple: there is a rule in Protein that **_every_ result of an expression is passed
    to the standard function that **deserializes** literals in Python**
    (reconstructs them from strings): [`ast.literal_eval()`](https://docs.python.org/3/library/ast.html#ast.literal_eval).

    | Result (String)           | Result (Deserialized)   | Type     |
    | ------------------------- | ----------------------- | -------- |
    | `"2.5"`                   | `2.5`                   | Float    |
    | `"'2.5'"`                 | `'2.5'`                 | String   |
    | `"['foo', 'bar', 'baz']"` | `['foo', 'bar', 'baz']` | Sequence |

    If that function succeeds in generating a scalar or a composite of sequences/mappings with
    scalars in them, then it is accepted as such. Otherwise, the result is treated as string.

    That rule works surprising well, and does what you would normally expect.
    
    What are the chances that you would accidentally produce a composite (sequence/mappings)
    when you had, in reality, intended to produce a string? They are _very_ low.
    
    Also, **`ast.literal_eval()` only produces literals**. It cannot call any code and,
    in particular, it cannot evaluate functions.


## Example: adding a function and a filter
We want `greet('Joe')` → `"Hello Joe"`, `greet('Joe') | shout` → `"HELLO JOE!!!"`, and the ability to call `greet` as a construct.

### Module (`greet.py`)
```python
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
### Protein file
```yaml
.import_module: greet.py
.define:
  name: Joe
data:
  greeting: "{{ greet(name) }}"
  loud: "{{ name | shout }}"
  app: "{{ app_name }}"
.greet:
  name: Joe
```

## Example: loading external data
Suppose we have a JSON file describing servers. We want a function that returns all servers in a given category.
### Module (`servers.py`)
```python
import json
from protein import ModuleEnvironment
SERVERS_FILE = "servers.json"
def define_env(env: ModuleEnvironment):
    @env.export
    def servers(category):
        with open(SERVERS_FILE) as f:
            data = json.load(f)
        return [
            (m["hostname"], m["ip"])
            for m in data
            if m["category"] == category
        ]
```
### Protein file
```yaml
.import_module: servers.py
.local
  live_servers: "{{ servers('live') }}"
```
Or as a construct:
```yaml
.servers:
  category: live
```

## Summary
Protein modules allow you to extend the language with Python code. Exports become available as constructs, as functions in Jinja expressions, as filters in Jinja expressions (if declared as such), and as variables. This dual integration makes Python modules a powerful way to enrich Protein with domain‑specific logic, external data, and reusable utilities.

