# Language reference

## Definitions

### General

- **YAMLpp**: A language based on ➙ YAML,
  which ➙ pre-processes a ➙ tree containing ➙ constructs into a plain YAML tree.

- **YAML™**: A data serialization language used in modern applications, mainly
  for complex, nested configuration files and as a foundation for domain-specific languages (see [Official definition](https://yaml.org/spec/))

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

### YAMLpp

- **Construct**: An instruction of YAMLpp ➙ pre-processing instructions that generates
  one or more YAML ➙ nodes. <br>
  All constructs are valid YAML.<br>
  Each construct has a name starting with a dot (`.`) and is presented as a ➙ block. <br>
  It is called a construct because it _constructs_ (builds) one or more nodes.


- **block** (YAMLpp) A piece of YAML code containing a ➙ sequence or ➙ mapping, with the key on the first line, and the content (node) indented in the following lines. 
  

- **Expression**: (YAMLpp) A ➙ value string containing a ➙ Jinja expression that returns a node. 

- **Expand**: (YAMLpp) To evaluate a ➙ Jinja expression and return a ➙ node.

- **Jinja**: The template engine that is used to calculate ➙ values in YAMLpp (see [documentation](https://jinja.palletsprojects.com/)).

- **module**: (YAMLpp) An imported piece of Python code (file or package) that provides variables, functions and [filters](https://jinja.palletsprojects.com/en/stable/templates/#filters) to the ➙ Jinja environment.



## General principles

1. All language constructs are expressed as valid YAML keys, prefixed with the symbol **`.`**.
They "run, transform the tree and disappear".
1. All other keys in the source file are plain YAML.
2. A value can be any YAML valid value. 
3. It can also be a string containing a [Jinja statement](https://jinja.palletsprojects.com/en/stable/).
   If the result string is a valid Python literal (a scalar, or a list or dictionary), then YAMLpp will convert it into a node.
4. The final output is a YAML tree where all YAMLpp constructs have disappeared.

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


!!! Tip "Usage"
    The `.do` construct is **necessary** to introduce a sequence of constructs within a map.

    ```yaml
    servers:
      foo: ...
      bar: ...
      baz: ...
      .do:
        # a series of instructions to create more key, value pairs
        - ...
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



### `.insert`
**Definition**: Insert and preprocesses another YAMLpp (or YAML) file, at this place in the tree.  
**Example**:
```yaml
.insert: "other.yaml"
```
This loads, inserts, and expands the contents of `other.yaml` into the current document.







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
**Definition**: Export the current portion of the tree into an external file  
**Example**:
```yaml
.export:
  .filename: "export/foo.yaml"
  .do: ... # thepart you wish to export.
```

The tree to be exported can be either plain YAML or contain YAMLpp constructs
(which will be expanded into YAML, before being exported).

**Output**:
None (the tree is exported to the external file)



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
is to use the environment variables of the OS, through the `@getenv()` function.

It be used in _any_ part of the YAMLpp tree.

```yaml
server:
  address: "{{ get_env('MY_SERVER`)}}"
```





## 🛠️ Troubleshooting

### Common Errors
1. **Undefined Variables**: Variable used in an expression is not defined in the current context or scope. Ensure all variables are declared within `.context` or passed correctly.  
2. **Duplicate keys**: A mapping (dictionary) can have only one key of each type.
   If a key is repeated, the parser will raise an error.
   If you are using the same key two times or more, it's likely that you should
   use a sequence (list) of mappings instead of a mapping.
   [This is principle applicable to YAML in general.]
3. **Unquoted Jinja expressions**: A YAMLpp file must be a valid YAML file. It means that values
  that contain a Jinja expression **must** be quoted: 
    - ❌ Incorrect: `message: Hello, {{ name }}!`
    - ✅ Correct: `message:"Hello, {{ name }}!"`
3. **Missing Functions or Modules**: Happens if a referenced function or module is not imported or defined. Verify `.module` imports and `.function` definitions.  
4. **Argument Mismatches**: When calling functions, ensure the number and order of arguments match the `.args` definition.  
5. **Syntax Errors**: Invalid YAML or incorrect use of YAMLpp directives can cause preprocessing failures. Validate YAML syntax and directive structure.  
6. **Incorrect Expression Syntax**: Jinja2 expressions must be properly formatted. Check for missing braces, quotes, or invalid operations.  

### Debugging Tips
- Check error messages carefully for line numbers (in the YAML file) and hints 
- Use minimal examples to isolate issues  
- Add Jinja variables that use variables defined in `.context` to print intermediate values  
- Validate YAML files with external linters   



