"""
Testing examples in the documentation.
"""

from protein import protein_comp
from protein.util import print_yaml

def test_function_to_create_abstraction():
    """
    Test the example function to create an abstraction from the documentation.
    """
    src = """
# docker-compose.Protein

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

version: "3.9"

services:
  .foreach:
    .values: [svc, "{{ services }}"]
    .do:
      - .print: "Defining service {{ svc }}"
      - .call: 
          .name: create_service
          .args: ["{{ svc }}"]
"""

    yaml, tree = protein_comp(src)
    print_yaml(yaml, "Evaluation")

    assert tree.services.api.image == "myorg/api:latest"
    assert tree.services.api.labels.maintainer == "Joe Bloe"
    assert tree.services.worker.ports[0] == "9090:9090"
    assert tree.services.frontend.labels.version == "1.0"
    assert len(tree.services) == 3