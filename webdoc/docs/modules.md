# Expanding Protein with Python Modules

## Purpose of a module

It can be useful to add new **functions** (in the Python sense) to the [expressions](reference.md#Protein) of Protein to:

1. Make it more expressive, for example by adding functions on strings, paths, mathematical objects, etc.
2. Extract data from other sources such as config files and databases.

Protein offers the possibility of using external Python modules that exports those variables and functions.

Those variables and functions can be used in two places:

1. As new _constructs_ of the Protein language (preceded by a dot).
2. Inside values, in expressions written in templating language called [Jinja](https://jinja.palletsprojects.com/en/stable/). You can refer to Python variables, or call Python functions.

### Scoping Rules
To understand how both these mechanisms work, it is necessary to understand that any variable or
function that is usable within a Protein program is stored in a **scope**
(a Protein program starts with its own scope). 

There is also an underlying scope created when the Protein interpreter is activated,
which contains some values and functions. To find the
value connected to a variable, Protein
consults first the current scope and then underlying scopes.

### Host Bindings

If you use the [`.define`](reference.md#define) construct,
you are storing variables into the _current_ scope.

A [`.function`](reference.md#function) construct stores a Protein function into the current scope.

You can **also** use variables and callables (functions) not defined by Protein,
which come from the **host** (the supporting language: Python).

The standard way to do that, is to define them in a **module**, written in Python. It is not
any Python package. It is a piece of Python program written in a specific way, which
defines variables and functions, and exposes them.

```python
"""
A sample module

(module.py)
"""
from protein import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    "Define your functions, filters and variables here"

    @env.export
    def my_function(...):
        """
        This function will be exported
        """
        ...
        return ...

    # this variable will be exported
    env.variables["foo"] = ....

```

Then the program must _import_ it:

```yaml
.import_module: path/to/module.py
```

All exported variables will become part of the current scope.

!!! Tip

    If you wish to avoid polluting the current scope, you can create a new
    scope, which will last as long as this node is being run.

    ```yaml
    servers: 
      .local:

      .import_module: path/to/module.py
      ...
    ```

## Example 1: Adding a function and a filter to expressions

### Problem
Suppose we want to have expressions that emphasize the name for a user:

- `greet('Joe')`, should return `Hello Joe`.
- and `greet('Joe')| shout` should return `HELLO JOE`. 

In Jinja `shout` is called a **[filter](https://jinja.palletsprojects.com/en/stable/templates/#filters)**. 
It is a special type of function, which
receives, as its first argument, the result of the expression before the pipe symbol (`|`).
It has only one argument (the input string),
that argument is implicit and no parentheses are needed.

This is what the Protein code should look like.

```yaml
.define:
  module: module1.py
  name: Joe
  sentence: "Hello world!"

data:
  #function contained in the module
  greeting: "{{ greet(name)}}"
  #filter contained in the module
  shout: "{{ name | shout }}"
  # variable contained in a module
  app_name: "{{app_name}}"
```

### Solution
To do so we need to declare the functions `greet()` and `shout()`, in a module 
(`greet.py`) before being allowed to use them.




This is done with the `define_env()` function, which takes the variable `env` as an argument.

Use:

- `env.export` as a decorator for a function you want to make visible in Jinja.
- `env.filter` as a decorator for a filter function.

Otherwise, you can also load directly variables (and functions) into the `env.variables` dictionary.

```python
"""
A sample module
"""

from protein import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    "Define your functions, filters and variables here"

    @env.export
    def greet(name: str) -> str:
        return f"Hello {name}"
    
    @env.filter
    def shout(value: str) -> str:
        return f"{value.upper()}!!!"
    
    env.variables["app_name"] = "Protein"
```

Finally, we should update the Protein file, by importing the module
(here, before the `data` map):

```yaml
.import_module greet.py
```


## Example 2: Calling an external module

### Problem
Suppose we have an external source file called `servers.json`:.

```json
[
  { "hostname": "apollo", "ip": "192.168.1.10", "category": "live" },
  { "hostname": "zephyr", "ip": "192.168.1.20", "category": "development" },
  { "hostname": "orion",  "ip": "192.168.1.30", "category": "test" },
  { "hostname": "athena", "ip": "192.168.1.40", "category": "live" }
]
```

Let's say that we want the list of live servers, for creating a YAML file that will handle the
development (e.g. in Kubernetes). 


### Solution

To do that we would need an expression that contains a call to a simple
function that returns a list of live machines we need to deploy.

```yaml
.local
    servers = "{{ servers('live') }}"
    ...
```

!!! Tip "Type conversions"
    Even though the expression `"{{ servers('live') }}"` is a string (that's required by YAML syntax),
    the result will be a Python list which will be then appropriately converted
    into a YAML sequence.

To do that, we need a ** module**, written in Python, and import it before using it 
(here, before the `.local` construct):

```yaml
.import_module: "my_module.py
```

Here is the Python module:

```python
"""
A sample module
"""
import json
from protein import ModuleEnvironment

SERVERS_FILE = "servers.json"  # source of truth

def define_env(env: ModuleEnvironment):
    "Define your functions, filters and variables here"

    @env.export
    def servers(category):
        """
        Return hostnames and IPs that match the given category.
        """
        with open(SERVERS_FILE) as f:
            data = json.load(f)
        return [(m["hostname"], m["ip"]) for m in data 
                            if m["category"] == category]

```

