# Advanced Aspects of Protein

## The Collapse Rules

### Definition

!!! Tip "Important"
    The **Collapse Rules** are key to understand how YAMLLpp results are processed by Protein
    constructs (`.do` and `.foreach`).

    It defines how Protein reduces empty **sequences** or **mappings** into simpler structures.
    It governs how Protein constructs produce final YAML structures.

    This rule is central to Protein, because it ensures that it behaves in a way that
    least surprises users.


### `.do` producing sequences

A sequence produced by a `.do` constructs collapses according to the following principles:

1. **Empty sequence → `None`**  
  An empty list represents the absence of a value

1. **Single‑element sequence → the element itself**  
  When a construct yields exactly one item, it is returned directly without wrapping.

1. **Otherwise → no collapse**  
  If the sequence does not meet the above conditions, it is returned unchanged.


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





### `.foreach` and the Collapse Rule

!!! Warning "`.foreach` always returns a sequence"
    It is important to understand that despite the fact that `.foreach` contains a `.do`
    sequence, it always returns a list.

    .foreach is, by essence, an operation on sequences (tables, lists, etc.)

    `.do` will collapse the results, but if there is one result left, then `.foreach` will return
    it as a _list of 1 element_.


#### Example


```yaml
result:
    .foreach:
    .values: [x, [1]]
    .do:
        - "{{x}}"
```

Wil result in:
```yaml
result:
    - 1
```


### `.foreach` producing a collected mapping

However the `.foreach` loop will do one additional thing: it collects of a **sequence of mappings of cardinality 1** produced by the `.do` construct into a single merged mapping.

#### Example

**Input**
```yaml
.local:
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

**Intermediate (before collecting)**
```yaml
accounts:
  - { joe:  { id: 1 } }
  - { jill: { id: 2 } }
```

Each element is a mapping with exactly one key → can be collected.

**Collected result**
```yaml
accounts:
  joe:
    id: 1
  jill:
    id: 2
```


#### How to disable collected mapping

For the cases where you wish to preserve the list of mappings with one key,
set the `collect_maps` attribute to `false`.


```yaml
.local:
  users:
    - { id: 1, name: joe }
    - { id: 2, name: jill }

accounts:
  .foreach:
    .values: [u, "{{ users }}"]
    .collect_mappings: false
    .do:
      "{{ u.name }}":
        id: "{{ u.id }}"
```


## How to escape  expressions

### The issue

When Protein renders a file, it uses Jinja as its templating engine to interpret keys and values.  
This means that **every occurrence of `{{ ... }}` is treated as a Jinja expression** and evaluated before Protein produces the final YAML output.

However, the system that ultimately consumes the generated YAML—such as GitHub Actions—may *also* have its own templating syntax. GitHub Actions, for example, uses the form `${{ ... }}` for its expressions. Because this syntax contains Jinja’s own `{{ ... }}` pattern, Jinja will try to evaluate the inner part first.

Consider this typical GitHub Actions snippet:

```yaml
steps:
  - name: Show GitHub ref
    run: 'echo "Current ref is ${{ github.ref }}"'
```

If this appears inside a Protein template, Jinja will **intercept** the `{{ github.ref }}` portion, attempt to evaluate it, and almost certainly fail—preventing the correct GitHub expression from ever reaching GitHub Actions.


### One-off solution

To prevent Jinja from interpreting GitHub’s `${{ ... }}` expressions, you must explicitly tell it to treat that part of the template as literal text.  
Ohe solution—[as described in the Jinja documentation](https://jinja.palletsprojects.com/en/stable/templates/#escaping)—is to wrap the affected section in a `{% raw %}` / `{% endraw %}` block.

Everything inside this block is passed through unchanged, allowing Protein to output the exact `${{ github.ref }}` expression that GitHub Actions expects.

!!! Warning "It will work only once"
    This is an _escape_ technique. If, for some reason, you are interpreting the same
    string _twice_ in expressions, then Protein will eventually attempt to apply the template.

#### Example: Protein‑idiomatic GitHub workflow generator

```yaml
.local:
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

- `.local` appears first and contains only data, not logic.
- The output file (here `github_workflow`) is a **single mapping key** with a `.template` body.
- The template uses Protein interpolation (`{{ workflow_name }}`) where appropriate.
- GitHub’s own `${{ … }}` syntax is preserved via `{% raw %}`.
- No unnecessary quoting, no heredocs, no shell tricks — just pure Protein.

If you want, I can show the idiomatic pattern for generating **multiple workflow files** using `.foreach` and the collapse rule.

### Permanent solution to avoid interpretation

The solution to guarantee that a string will _never_ be used as a template,
is to the `#!literal` prefix in front of it, for example:

```yaml
.text: "#!literal Hello {{ name }}"
```

This will guarantee that Protein will never consider that string as a template, until
the value is exported:

- When the string will be output as YAML or JSON, etc., it will appear without the prefix.
(`Hello {{ name }}`).
- The [`.write_buffer`](reference.md#write_buffer) construct will also strip the prefix.


### Protein‑idiomatic multi‑workflow generator

```yaml
.local:
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



- **`.local` first** — pure data, no logic.
- **Top‑level directory key** (`.github/workflows:`) — Protein treats it as a mapping.
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





