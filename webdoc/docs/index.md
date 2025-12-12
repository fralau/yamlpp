# YAML File Preprocessor (YAMLpp)

## Problem
YAML is an excellent file format but it is essentially static. Sometimes, the content of a YAML file must change according to circumstances (typically when the environment changes or when you have different
configuratons for test or production, etc.). 


Manually maintaining different versions with the same boiler-plate code can be time-consuming and error-prone.


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

!!!Tip "YAMLpp obeys the rules of YAML syntax"
    - It provides declarative constructs without breaking YAML syntax. 
    - It allows modular, reusable, and expressive constructs that generate YAML files.

!!!Tip "Output is not limited to YAML"
       You can also generate other formats, such as [JSON](https://www.w3schools.com/whatis/whatis_json.asp) or [TOML](https://toml.io/en/).
       
       One possible application is to generate JSON files dynamically.


## 🚀 Quickstart

### Installation
```sh
pip install yamlpp-lang
```

### Command-line usage
```sh
yamlpp input.yaml -o output.yaml
```
- `input.yaml` → your YAML file with YPP directives  
- `output.yaml` → the fully expanded YAML after preprocessing  

To consult the help:
```sh
yamlpp --help
```


### Introduction to the Python API
```python
from yamlpp import Interpreter

FILENAME = 'test2.yaml'
i = Interpreter()
i.load(FILENAME)

tree = i.render()
result = i.yaml # contains the yaml file


# Access to fields of the final tree
url = tree['server'].['url'] # 'http://test.example.com'

# Access by dot notation
url = tree.server.url
```

