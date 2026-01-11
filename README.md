# Protein, a Data Composer and Templating Tool


## Problem
Nowadays, a lot of software is piloted by data files, typically JSON or YAML files.


JSON and YAML are excellent file formats but they are essentially static. Sometimes, the content of a file must change according to circumstances (typically when the environment changes or when you have different
configuratons for test or production, etc.). 


Manually maintaining different versions with the same boiler-plate data can be time-consuming and error-prone.


## Introducing YAMLpp
What if we had a way to generate a new data file (or more than one) according to a single
set of source data?

The purpose of **Protein** is to help programmers prepare data files in various formats,
(JSON, YAML, but also HTML, etc.) with rules that produce your data according to source data. 

It extends standard YAML with constructs for variable declaration, conditionals, iteration, functions, importing and exporting YAML files, and importing Python modules.

YAMLpp is a macro language, since it manipulates the YAML tree on which it resides.


Here is a simple example:

**YAMLpp**:
```yaml
.local:
  name: "Alice"

message: "Hello, {{ name }}!"
```
**Output**:
```yaml
message: "Hello, Alice!"
```


### General principles

The language is composed of **constructs**, which are denoted keys starting with a dot (`.`), such
as `.local`, `.if`, `.switch`, etc.

The YAMLpp preprocessor uses these constructs modify the tree, and the constructs disappear.

The result is pure YAML.


**YAMLpp obeys the rules of YAML syntax:**
- It provides declarative constructs without breaking YAML syntax. 
- It allows modular, reusable, and expressive constructs that create YAML files



## 🚀 Quickstart

### Installation
```bash
pip install yamlpp-lang
```

### Command-line usage
```bash
yamlpp input.yaml -o output.yaml
```
- `input.yaml` → your YAML file with YAMLpp directives  
- `output.yaml` → the fully expanded YAML after preprocessing  

To consult the help:
```sh
yamlpp --help
```


### Python API
```python
from protein import Interpreter

FILENAME = 'my_file.yaml'
i = Interpreter()

# the initial (source) tree:
initial_tree = i.load(FILENAME)

# the destination (target) tree (pure YAML):
tree = i.render()

# print the resulting YAML
print(i.yaml)
```







## 🔧 A Sample of Protein Constructs

| Construct            | Purpose                                                            | Minimal Example                                                                                     |
| -------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| **`.local`**         | Define local variables valid for siblings and descendants.         | .local:<br>  name: "Alice"<br>message: "Hello {{ name }}"                                           |
| **`.do`**            | Execute a sequence or map of instructions.                         | .do:<br>  - step: "Init"<br>  - step: "Run"                                                         |
| **`.foreach`**       | Iterate over values with a loop body.                              | .local:<br>  items: [1,2]<br>.foreach:<br>  .values: [x, items]<br>  .do:<br>    - val: "{{ x }}"   |
| **`.switch`**        | Branch to a different node based on an expression and cases.       | .switch:<br>  .expr: "{{ color }}"<br>  .cases:<br>    red: {msg: "Stop"}<br>  .default: {msg: "?"} |
| **`.if`**            | Conditional node creation with `then` and `else`.                  | .if:<br>  .cond: "{{ x>0 }}"<br>  .then: {res: "Pos"}<br>  .else: {res: "Neg"}                      |
| **`.load`**          | Insert and preprocess another YAMLpp (or YAML) file.               | .import_module: "other.yaml"                                                                        |
| **`.function`**      | Define a reusable block with arguments and a body.                 | .function:<br>  .name: "greet"<br>  .args: ["n"]<br>  .do:<br>    - msg: "Hi {{ n }}"               |
| **`.call`**          | Invoke a previously defined function with arguments.               | .call:<br>  .name: "greet"<br>  .args: ["Bob"]                                                      |
| **`.import_module`** | Import a Python module exposing functions, filters, and variables. | .module: "module.py"                                                                                |
| **`.export`**        | Export a portion of the tree into an external file.                | .export:<br>  .filename: "out.yaml"<br>  .do:<br>    - foo: "bar"                                   |



