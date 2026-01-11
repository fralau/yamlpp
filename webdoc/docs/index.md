# Protein Data Composer

## Problem

Nowadays, a lot of software is piloted by data files, typically JSON or YAML files.


JSON and YAML are excellent file formats but they are essentially static. Sometimes, the content of a file must change according to circumstances (typically when the environment changes or when you have different
configuratons for test or production, etc.). 


Manually maintaining different versions with the same boiler-plate data can be time-consuming and error-prone.


## Introducing Protein
What if we had a way to generate a new data file (or more than one) according to a single
set of source data?

The purpose of **Protein** is to help programmers prepare data files in various formats,
(JSON, YAML, but also HTML, etc.) with rules that produce your data according to source data. 

It extends standard YAML with constructs for variable declaration, conditionals, iteration, functions, importing and exporting YAML files, and importing Python modules.

Protein is a macro language, since it manipulates the YAML tree on which it resides.


Here is a simple example:

**Protein**:
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

The Protein preprocessor uses these constructs modify the tree, and the constructs disappear.

The result is pure YAML.

!!!Tip "Protein obeys the rules of YAML syntax"
    - It provides declarative constructs without breaking YAML syntax. 
    - It allows modular, reusable, and expressive constructs that generate YAML files.

!!!Tip "Output is not limited to YAML"
       You can also generate other formats, such as [JSON](https://www.w3schools.com/whatis/whatis_json.asp) or [TOML](https://toml.io/en/).
       
       One possible application is to generate JSON files dynamically.


## 🚀 Quickstart

### Installation
```sh
pip install protein-lang
```

### Command-line usage
```sh
protein input.yaml -o output.yaml
```
- `input.yaml` → your YAML file with YPP directives  
- `output.yaml` → the fully expanded YAML after preprocessing  

To consult the help:
```sh
protein --help
```


### Introduction to the Python API
```python
from protein import Interpreter

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

