
"""
Test Jinja2 escaping ({% raw %}...{% endraw %})
"""

from yamlpp import Interpreter
from yamlpp.util import print_yaml


def test_single_workflow_with_raw():
    "Test the {% raw %}...{% endraw %} idiom"
    yaml_source = """
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
"""

    i = Interpreter()
    i.load_text(yaml_source)
    workflow = i.tree

    print_yaml(i.yaml)

    # Check that the workflow name was interpolated
    assert "name" in workflow
    workflow['name'] == 'Example Workflow'

    # Check that the raw block preserved the GitHub expression
    assert 'echo "Current ref is ${{ github.ref }}"' in workflow.jobs.demo.steps[0].run


def test_multiple_workflows_with_foreach_and_raw():
    "Test the {% raw %}...{% endraw %} idiom within a .foreach"
    yaml_source = """
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
"""

    i = Interpreter()
    i.load_text(yaml_source)
    workflows = i.tree

    print_yaml(i.yaml)
    # Expected keys after collapse
    assert list(workflows.keys()) == ["build.yml", "release.yml"]

    build = workflows["build.yml"]
    release = workflows["release.yml"]

    # Check interpolation of workflow names
    assert 'echo "Value is ${{ github.ref }}"' in build.jobs.steps[0].run
    assert 'echo "Value is ${{ github.ref }}"' in release.jobs.steps[0].run

