# YAML File Preprocessor (YAMLpp)

## Problem
YAML is an excellent file format but it is essentially static. Sometimes, the content of a YAML file must change according to circumstances (typically when the environment changes or when you have different
configuratons for test or production, etc.).

Manually maintaining different versions can be time-consuming and error-prone.


## Introducing YAMLpp
What if we had a way to generate a new YAML file (or more than one) according to a single pattern?

The purpose of **YAML Preprocessor (YAMLpp)** is to help programmers prepare YAML files from a template, with rules that produce the YAML tree according to source data. It extends standard YAML with constructs for variable declaration, conditionals, iteration, functions, importing and exporting YAML files, and importing Python modules.

YAMLpp is a macro language, since it manipulates the YAML tree on which it resides.


Here is a simple example:

**YAMLpp**:
```yaml
.context:
  name: "Alice"

message: "Hello, {{ name }}!"
```
**Output**:
```yaml
message: "Hello, Alice!"
```


### General principles

1. All language constructs are expressed as valid YAML keys, prefixed with the symbol **`.`**.
They "run, transform the tree and disappear".
1. All other keys in the source file are plain YAML.
2. Values can be any YAML valid value. 
3. They can also be a string containing a [Jinja statement](https://jinja.palletsprojects.com/en/stable/).
   If the result string is a valid Python literal (a scalar, or a list or dictionary), then YAMLpp will convert it.
4. The output is a YAML tree where all YAMLpp constructs have disappeared.

**YAMLpp obeys the rules of YAML syntax:**
- It provides declarative constructs without breaking YAML syntax. 
- It allows modular, reusable, and expressive constructs that create YAML files



## 🚀 Quickstart

### Installation
```bash
pip install yamlpp
```

### Command-line usage
```bash
yamlpp input.yaml > output.yaml
```
- `input.yaml` → your YAML file with YPP directives  
- `output.yaml` → the fully expanded YAML after preprocessing  

### Python API
```python
from yamlpp import preprocess

with open("input.yaml") as f:
    data = preprocess(f.read())
print(data)
```



## 🔧 Constructs

Each construct is defined below with its purpose and an example.

### `.context`
**Definition**: Defines a local scope of variables for a block.

You can define a `.context` block at any node of the tree.
The variables defined are valid for all the siblings and the descendents
(but are not accessible in part of the tree that are higher than this block.)

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
**Definition**: Executes a sequence of instructions in order.
You could also generate a map (dictionary) instead of a sequence (list).

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
**Definition**: Branches to a different YAML node, based on an expression and cases.  
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
**Definition**: Creates a YAML node, according to condition, with then and else.  
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



### `.import`
**Definition**: Imports and preprocesses another YAMLpp (or YAML) file.  
**Example**:
```yaml
.import: "other.yaml"
```
This loads and expands the contents of `other.yaml` into the current document.



#



### `.function`
**Definition**: Defines a reusable function with arguments and a body. Arguments are positional.

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
**Definition**: Invokes a previously defined function with arguments.  
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

## `.module`
**Definition**: Imports a Python module, exposing functions and filters to the Jinja expressions.
  
**Example**:
```yaml
.module: "module.py"
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
**Definition**: Exports the current portion of the tree into an external file  
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



