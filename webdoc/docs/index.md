# Protein Data Composer

## Problem

Nowadays, a lot of software is driven by data files, typically JSON or YAML files.


JSON and YAML are excellent file formats but they are essentially static. Sometimes, the content of a file must change according to circumstances (typically when the environment changes or when you have different
configuratons for test or production, etc.). 


Manually maintaining different versions with the same boiler-plate data, can be time-consuming and error-prone.


## Introducing Protein
What if there was a way to generate a new data file (or more than one) according to a single
set of data? The purpose of **Protein** is to help programmers prepare data files in various formats,
(JSON, YAML, but also Markdown,  bbHTML, CSS, etc.) with rules that produce your various data
files, according to the same set of source data. 

Protein extends standard YAML with **constructs** (commands) for declaration of variables, conditionals, iteration, functions, importing and exporting YAML files, and importing Python modules.


!!! Important
    Protein does **not** work like other languages, where a program is
    a sequence of commands: Protein allows you to **enrich** an existing YAML tree with constructs (commands starting with a dot, such as `.load`) that will manipulate that tree.

    1. In Protein, you find constructs mixed with normal YAML elements.
    2. Every construct is executed in turn.
    3. When a construct is executed, it performs a certain transformation
    or action and then it **vanishes** (disappears)
    4. The execution of a Protein program stops when all constructs have been
    executed and have vanished.




Protein is a macro language, since it manipulates the YAML tree on which it resides.




Here is a simple example, which does not much:

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

The language is composed of **constructs** (Protein commands), denoted by keys starting with a dot (`.`), such
as `.local`, `.if`, `.switch`, etc.



**The Protein preprocessor uses these constructs to modify the tree, and the constructs vanish.**

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

Protein offers a Python interface.

#### Simple interface

The simplest way is to use the `protein_comp()` function:

```python
from protein import protein_comp

yaml_text = """
...
"""

yaml, result = protein_comp(yaml_text)
```

You can also specify a default ("source") directory, where input and output
files are expected to be (otherwise it will be by default your current directory).


### Using an Interpreter object

```python
from protein import Interpreter

FILENAME = 'test2.yaml'
i = Interpreter() # by default 
tree = i.load(FILENAME) # the is the compiled file 
yaml_output = i.yaml # contains the yaml file


# Access to fields of the final tree
url = tree['server'].['url'] # 'http://test.example.com'

# Access by dot notation
url = tree.server.url
```

When defining the Interpreter object, you can also specify a default ("source") directory,
where input and output
files are expected to be (otherwise it will be by default the location of your input file,
or your current directory).


You can also suspend the rendering:

```python
i = Interpreter()
i.load(FILENAME, render=False) # suspend rendering

# now render:
tree = i.render_tree()
yaml_output = i.yaml # if render_tree() was not called before, it will trigger it.
```
