# YAML File Preprocessor (YAMLpp)

## Problem
YAML is an excellent file format but it is essentially static. Sometimes, the content of a YAML file must change according to circumstances (typically when the environment changes or when you have different
configuratons for test or production, etc.).

Manually maintaining different versions can be time-consuming and error-prone.


## Introducing YAMLpp
What if we had a way to generate a new YAML file (or more than one) according to a single pattern?

The purpose of **YAML Preprocessor (YAMLpp)** is to help programmers prepare YAML files from a template, with rules that produce the appropriate results according to source data. It extends standard YAML with constructs for variable declaration, conditionals, iteration, functions, importing and exporting YAML files, and importing Python modules.  


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

> All language constructs are expressed as valid YAML keys, prefixed with the symbol **`.`**.
> They "run, transform the tree and disappear".

1. All other keys in the source file are plain YAML.
2. Values can be any YAML valid value. 
3. They can also be a string containing a [Jinja statement](https://jinja.palletsprojects.com/en/stable/).
   If the result string is a valid Python literal (a list or a dictionary), then YAMLpp will convert it.
4. The output is a YAML file where all YAMLpp constructs have disappeared, and have been
replaced by a new tree.

**YAMLpp obeys the rules of YAML syntax:**
- It provides declarative constructs without breaking YAML syntax. 
- It allows modular, reusable, and expressive constructs to create YAML files



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
**Definition**: Defines a reusable function with arguments and a body. 

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

## 🛠️ Troubleshooting

### Common Errors
- **Undefined Variables**: Variable used in an expression is not defined in the current context or scope. Ensure all variables are declared within `.context` or passed correctly.  
- **Unquoted Jinja expressions**: A YAMLpp file must be a valid YAML file. It means that values
  that contain a Jinja expression **must** be quoted: 
    - ❌ Incorrect: `message: Hello, {{ name }}!`
    - ✅ Correct: `message:"Hello, {{ name }}!"`
- **Missing Functions or Modules**: Happens if a referenced function or module is not imported or defined. Verify `.module` imports and `.function` definitions.  
- **Argument Mismatches**: When calling functions, ensure the number and order of arguments match the `.args` definition.  
- **Syntax Errors**: Invalid YAML or incorrect use of YAMLpp directives can cause preprocessing failures. Validate YAML syntax and directive structure.  
- **Incorrect Expression Syntax**: Jinja2 expressions must be properly formatted. Check for missing braces, quotes, or invalid operations.  

### Debugging Tips
- Check error messages carefully for line numbers (in the YAML file) and hints 
- Use minimal examples to isolate issues  
- Add Jinja variables that use variables defined in `.context` to print intermediate values  
- Validate YAML files with external linters   



