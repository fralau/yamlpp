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

The language is composed of **constructs**, which are denoted keys starting with a dot (`.`), such
as `.context`, `.if`, `.switch`, etc.

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
from yamlpp import Interpreter

FILENAME = 'my_file.yaml'
i = Interpreter()

# the initial (source) tree:
initial_tree = i.load(FILENAME)

# the destination (target) tree (pure YAML):
tree = i.render()

# print the resulting YAML
print(i.yaml)
```







## 🔧 YAMLpp Constructs (Quick Reference)

| Construct   | Purpose | Minimal Example |
|-------------|---------|-----------------|
| **`.context`** | Define local variables valid for siblings and descendants. | .context:<br>  name: "Alice"<br>message: "Hello {{ name }}" |
| **`.do`** | Execute a sequence or map of instructions. | .do:<br>  - step: "Init"<br>  - step: "Run" |
| **`.foreach`** | Iterate over values with a loop body. | .context:<br>  items: [1,2]<br>.foreach:<br>  .values: [x, items]<br>  .do:<br>    - val: "{{ x }}" |
| **`.switch`** | Branch to a different node based on an expression and cases. | .switch:<br>  .expr: "{{ color }}"<br>  .cases:<br>    red: {msg: "Stop"}<br>  .default: {msg: "?"} |
| **`.if`** | Conditional node creation with `then` and `else`. | .if:<br>  .cond: "{{ x>0 }}"<br>  .then: {res: "Pos"}<br>  .else: {res: "Neg"} |
| **`.load`** | Insert and preprocess another YAMLpp (or YAML) file. | .import: "other.yaml" |
| **`.function`** | Define a reusable block with arguments and a body. | .function:<br>  .name: "greet"<br>  .args: ["n"]<br>  .do:<br>    - msg: "Hi {{ n }}" |
| **`.call`** | Invoke a previously defined function with arguments. | .call:<br>  .name: "greet"<br>  .args: ["Bob"] |
| **`.import`** | Import a Python module exposing functions, filters, and variables. | .module: "module.py" |
| **`.export`** | Export a portion of the tree into an external file. | .export:<br>  .filename: "out.yaml"<br>  .do:<br>    - foo: "bar" |



