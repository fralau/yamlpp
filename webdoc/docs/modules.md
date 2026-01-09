# Expanding YAMLpp with Python Modules

## Purpose of a module

It can be useful to add new **functions** (in the Python sense) to the [expressions](reference.md#yamlpp) of YAMLpp to:

1. Make it more expressive, for example by adding functions on strings, paths, mathematical objects, etc.
2. Extract data from other sources such as config files and databases.

YAMLpp offers the possibility of using external Python modules that exports those functions.

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

This is what the YAMLpp code should look like.

```yaml
.local:
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

from yamlpp import ModuleEnvironment

def define_env(env: ModuleEnvironment):
    "Define your functions, filters and variables here"

    @env.export
    def greet(name: str) -> str:
        return f"Hello {name}"
    
    @env.filter
    def shout(value: str) -> str:
        return f"{value.upper()}!!!"
    
    env.variables["app_name"] = "YAMLpp"
```

Finally, we should update the YAMLpp file, by importing the module
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
from yamlpp import ModuleEnvironment

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

