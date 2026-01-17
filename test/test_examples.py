"""
Testing examples in the documentation.
"""

from protein import protein_comp
from protein.util import print_yaml

def test_usage_example(tmp_path):
    """
    Test the example function to produce a YAML file and a README file.
    """
    src = """
# Example: Generate a Docker Compose file with a reusable function, and write a README

.define:
  maintainer: "Joe Bloe"
  version: "'1.0'"
  services:
    - {name: "api", image: "myorg/api:latest", port: 8080}
    - {name: "worker", image: "myorg/worker:latest", port: 9090}
    - {name: "frontend", image: "myorg/frontend:latest", port: 3000}

# Define a reusable function for a service
.function:
  .name: create_service
  .args: [svc]
  .do:
    "{{ svc.name }}":
      image: "{{ svc.image }}"
      restart: always
      ports:
        - "{{ svc.port }}:{{ svc.port }}"
      labels:
        maintainer: "{{ maintainer }}"
        version: "{{ version }}"

# this will go to the standard ouptut:
services:
  .foreach:
    .values: [svc, "{{ services }}"]
    .do:
      - .print: "Defining service {{ svc }}"
      - .call: 
          .name: create_service
          .args: ["{{ svc }}"]


.write:
    # this will write to a file in the working directory
    .filename: README.md
    .text: |
        # Docker Compose File
        
        (This docker-compose file was generated using Protein.)

        It defines the following services:
        
        | Service | Image | Port |
        |---------|-------|------|
        {% for svc in services %}
        | {{ svc.name }} | {{ svc.image }} | {{ svc.port }} |
        {% endfor %}
"""

    yaml, tree = protein_comp(src, working_dir=tmp_path)
    print_yaml(yaml, "Evaluation")

    assert tree.services.api.image == "myorg/api:latest"
    assert tree.services.api.labels.maintainer == "Joe Bloe"
    assert tree.services.worker.ports[0] == "9090:9090"
    assert tree.services.frontend.labels.version == "1.0"
    assert len(tree.services) == 3

    with open(tmp_path / "README.md") as f:
        readme_content = f.read()
    assert "barbaz" not in readme_content
    assert "# Docker Compose File" in readme_content
    assert "| api | myorg/api:latest | 8080 |" in readme_content
    assert "| worker | myorg/worker:latest | 9090 |" in readme_content
    assert "| frontend | myorg/frontend:latest | 3000 |" in readme_content