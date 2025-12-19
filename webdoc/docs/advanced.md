# Advanced Aspects of YAMLpp

## The Collapse Rule

### Definition

!!! Note "Important"
    The **Collapse Rule** is key to understand how YAMLLpp results are processed.

    It defines how YAMLpp reduces **sequences** into simpler semantic forms.
    It governs how loop expansions and other generative constructs produce final YAML structures.

    This rule is central to YAMLpp semantics because it ensures that constructs like `.foreach` naturally produce mappings rather than lists of tiny maps, yielding intuitive and structurally coherent YAML output

A sequence collapses according to the following principles:

1. **Empty sequence → `None`**  
  An empty list represents the absence of a value

2. **Single‑element sequence → the element itself**  
  When a construct yields exactly one item, it is returned directly without wrapping.

3. **Multi‑element sequence of 1‑key mappings → merged mapping**  
  If every element in the sequence is a mapping of cardinality one, the sequence is interpreted as a distributed mapping.  
  The result is a single mapping whose keys and values come from merging each element’s sole key–value pair.

4. **Otherwise → no collapse**  
  If the sequence does not meet the above conditions, it is returned unchanged.


### Examples

#### 1. Empty sequence → `None`

**Input**
```yaml
items: []
```

**Collapsed result**
```yaml
items: null
```



#### 2. Single‑element sequence → the element itself

**Input**
```yaml
items:
  - apple
```

**Collapsed result**
```yaml
items: apple
```


#### 3. Sequence of 1‑key mappings → merged mapping

**Input**
```yaml
items:
  - { a: 1 }
  - { b: 2 }
  - { c: 3 }
```

**Collapsed result**
```yaml
items:
  a: 1
  b: 2
  c: 3
```


### Example: `.foreach` producing a collapsed mapping

This example shows how a `.foreach` loop naturally triggers the collapse rule by generating a **sequence of mappings of cardinality 1**, which YAMLpp then collapses into a single merged mapping.

**Input**
```yaml
.context:
  users:
    - { id: 1, name: joe }
    - { id: 2, name: jill }

accounts:
  .foreach:
    .values: [u, "{{ users }}"]
    .do:
      "{{ u.name }}":
        id: "{{ u.id }}"
```

**Intermediate (before collapse)**
```yaml
accounts:
  - { joe:  { id: 1 } }
  - { jill: { id: 2 } }
```

Each element is a mapping with exactly one key → collapsible.

**Collapsed result**
```yaml
accounts:
  joe:
    id: 1
  jill:
    id: 2
```

This demonstrates how `.foreach` integrates seamlessly with the collapse rule to produce clean, natural YAML structures.

## How to escape  expressions

### The issue

When YAMLpp renders a file, it uses Jinja as its templating engine to interpret keys and values.  
This means that **every occurrence of `{{ ... }}` is treated as a Jinja expression** and evaluated before YAMLpp produces the final YAML output.

However, the system that ultimately consumes the generated YAML—such as GitHub Actions—may *also* have its own templating syntax. GitHub Actions, for example, uses the form `${{ ... }}` for its expressions. Because this syntax contains Jinja’s own `{{ ... }}` pattern, Jinja will try to evaluate the inner part first.

Consider this typical GitHub Actions snippet:

```yaml
steps:
  - name: Show GitHub ref
    run: 'echo "Current ref is ${{ github.ref }}"'
```

If this appears inside a YAMLpp template, Jinja will **intercept** the `{{ github.ref }}` portion, attempt to evaluate it, and almost certainly fail—preventing the correct GitHub expression from ever reaching GitHub Actions.


### The solution

To prevent Jinja from interpreting GitHub’s `${{ ... }}` expressions, you must explicitly tell it to treat that part of the template as literal text.  
The solution—[as described in the Jinja documentation](https://jinja.palletsprojects.com/en/stable/templates/#escaping)—is to wrap the affected section in a `{% raw %}` / `{% endraw %}` block.

Everything inside this block is passed through unchanged, allowing YAMLpp to output the exact `${{ github.ref }}` expression that GitHub Actions expects.



### Example: YAMLpp‑idiomatic GitHub workflow generator

```yaml
.context:
  workflow_name: Example Workflow


name: "{{ workflow_name }}"

on:
    push:
    branches: [ main ]

jobs:
    demo:
        runs-on: ubuntu-latest
        steps:
            - name: Show GitHub ref
              run: |
                {% raw %}
                echo "Current ref is ${{ github.ref }}"
                {% endraw %}
```

- `.context` appears first and contains only data, not logic.
- The output file (here `github_workflow`) is a **single mapping key** with a `.template` body.
- The template uses YAMLpp interpolation (`{{ workflow_name }}`) where appropriate.
- GitHub’s own `${{ … }}` syntax is preserved via `{% raw %}`.
- No unnecessary quoting, no heredocs, no shell tricks — just pure YAMLpp.

If you want, I can show the idiomatic pattern for generating **multiple workflow files** using `.foreach` and the collapse rule.



### YAMLpp‑idiomatic multi‑workflow generator

```yaml
.context:
  workflows:
    - { name: build,   version: 0.0.1 }
    - { name: release, version: 0.0.2 }


.foreach:
    .values: [w, "{{ workflows }}"]
    .do:
        "{{ w.name }}.yml":
            name: "{{ w.name | capitalize }}"

            on:
                push:
                    branches: [ main ]

            jobs:
                runs-on: ubuntu-latest
                steps:
                    - name: Show GitHub value
                      run: |
                        {% raw %}
                        echo "Value is ${{ github.ref }}"
                        {% endraw %}
```



- **`.context` first** — pure data, no logic.
- **Top‑level directory key** (`.github/workflows:`) — YAMLpp treats it as a mapping.
- **`.foreach`** produces a *sequence of 1‑key maps*, which collapses into a mapping of workflow files.
- **Each iteration produces a file** named `"{{ w.name }}.yml"`.
- **`.template`** emits literal GitHub workflow YAML.
- **`{% raw %}`** ensures GitHub’s `${{ … }}` syntax survives untouched.
- **Collapse rule** merges all generated workflow files into a single mapping under `.github/workflows`.

The result is a directory‑like structure:

```yaml
.github/workflows:
  build.yml:   "<template output>"
  release.yml: "<template output>"
```

