# 📘 YAMLpp Programming Guide

## Introduction

The purpose of this page is to introduce two real cases.

## 📘 Example: Generation of several YAML files from a template

### 1. The Real‑World Problem
The purpose is to generate [Kubernetes](https://kubernetes.io/docs/concepts/overview/) manifests
(specification files) for deploying different environments:

- **dev** → 1 replica, image tag `latest`
- **test** → 2 replicas, image tag `candidate`
- **prod** → 5 replicas, image tag `stable`

Maintaining three separate YAML files is error‑prone.  
YAMLpp lets you declare **one template** and generate all variants.


### Step‑by‑Step Guide

#### Step 1 — Define Context
Set environment‑specific parameters in a `.context` block.

```yaml
.context:
  envs:
    dev:
      replicas: 1
      image_tag: "latest"
    test:
      replicas: 2
      image_tag: "candidate"
    prod:
      replicas: 5
      image_tag: "stable"
```


#### Step 2 — Iterate over Environments
Use `.foreach` to loop through each environment.

```yaml
.foreach:
  .values: [env, envs]
  .do:
    - .context:
        cfg: "{{ envs[env] }}"
      .export:
        .filename: "deployments/{{ env }}.yaml"
        .do:
          apiVersion: apps/v1
          kind: Deployment
          metadata:
            name: "myapp-{{ env }}"
          spec:
            replicas: "{{ cfg.replicas }}"
            selector:
              matchLabels:
                app: myapp
            template:
              metadata:
                labels:
                  app: myapp
              spec:
                containers:
                  - name: myapp
                    image: "myapp:{{ cfg.image_tag }}"
```


#### Step 3 — Run YAMLpp
```bash
yamlpp k8s-template.yaml
```

This produces three files:
- `deployments/dev.yaml`
- `deployments/test.yaml`
- `deployments/prod.yaml`


### Output

**`deployments/prod.yaml`**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-prod
spec:
  replicas: 5
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myapp:stable
```



### Key Programming Patterns

- **Variables with `.context`** → keep environment configs centralized.  
- **Loops with `.foreach`** → generate multiple files from one template.  
- **Exports with `.export`** → write each variant to disk.  
- **Jinja expressions** → interpolate values cleanly.  



### Why This Matters
- One source of truth → fewer mistakes.  
- Easy scaling → add new environments by editing `.context`.  
- Reusable → same template works for Kubernetes, Docker Compose, or CI pipelines.  






## 📘 Example: Use of a function to create abstraction

### The Real-World-Problem

The purpose is to generate a Compose file for Docker, describing a set of services.
To simplify make the code more abstract, we use a function. 


```yaml
# docker-compose.yamlpp

.context:
  maintainer: "Laurent"
  version: "1.0"
  services:
    - {name: "api", image: "myorg/api:latest", port: 8080}
    - {name: "worker", image: "myorg/worker:latest", port: 9090}
    - {name: "frontend", image: "myorg/frontend:latest", port: 3000}

# Define a reusable function for a service
.function
  .name: service:
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
  .foreach svc in services:
    .call service(svc)
```


### Output

```yaml
version: "3.9"

services:
  api:
    image: "myorg/api:latest"
    restart: always
    ports:
      - "8080:8080"
    labels:
      maintainer: "Laurent"
      version: "1.0"

  worker:
    image: "myorg/worker:latest"
    restart: always
    ports:
      - "9090:9090"
    labels:
      maintainer: "Laurent"
      version: "1.0"

  frontend:
    image: "myorg/frontend:latest"
    restart: always
    ports:
      - "3000:3000"
    labels:
      maintainer: "Laurent"
      version: "1.0"
```


### Why This Is Sensible
- The **function** defines the service pattern once.  
- `.context` holds the sequence of service definitions.  
- `.foreach` iterates over them, and `.call` expands each into a full service block.  
- We get both **abstraction** (via the function) and **compactness** (via the sequence).  


## 📘 Example: Forming a configuration from a database query

Suppose we have an SQL database, with a table `servers`:


| id | name   | ip          |
|----|--------|-------------|
| 1  | alpha  | 10.0.0.1    |
| 2  | beta   | 10.0.0.2    |
| 3  | gamma  | 10.0.0.3    |

We wish to use it to 

This tutorial explains the exact sequence:

```
.def_sql:
    .name: db
    .url: "sqlite:///foo.sqlite"
                       
.context:
    servers:
        .load_sql:
            .engine: db
            .query: "SELECT id, name, ip FROM servers ORDER BY id"

config:
  .foreach: 
    .values: [server, "{{servers}}"]
    .do:
        - name: "{{ server.name }}"
          address: "{{ server.ip }}"
```

Each block is processed in order by the YAMLpp interpreter.  
Here is what happens step by step.

---

### 1. Define an SQL engine

```
.def_sql:
    .name: db
    .url: "sqlite:///$filename"
```

**What this does**

- Creates a new SQL engine named `db`.
- The engine uses a SQLite URL.
- `$filename` is substituted with the current file’s path.

**Result**

You now have a usable SQL engine called `db` stored in the interpreter’s engine registry.

---

### 2. Load SQL data into the context

```
.context:
    servers:
        .load_sql:
            .engine: db
            .query: "SELECT id, name, ip FROM servers ORDER BY id"
```

**What this does**

- Creates a context variable named `servers`.
- Executes the SQL query using engine `db`.
- Fetches rows from the `servers` table.
- Converts each row into a dictionary like:

```
{ "id": 1, "name": "alpha", "ip": "10.0.0.1" }
```

**Result**

`servers` becomes a list of dictionaries:

```
[
  {id: 1, name: "alpha", ip: "10.0.0.1"},
  {id: 2, name: "beta",  ip: "10.0.0.2"},
  ...
]
```

This list is now available for interpolation and iteration.

---

### 3. Iterate over the servers

```
config:
  .foreach: 
    .values: [server, "{{servers}}"]
    .do:
        - name: "{{ server.name }}"
          address: "{{ server.ip }}"
```

**What this does**

**`.values: [server, "{{servers}}"]`**

- Defines the loop variable name: `server`.
- Expands `{{servers}}` into the actual list of server dictionaries.

**`.do:`**

For each server, YAMLpp produces:

```
- name: "<value of server.name>"
  address: "<value of server.ip>"
```

**Example output**

```
config:
  - name: "alpha"
    address: "10.0.0.1"

  - name: "beta"
    address: "10.0.0.2"
```

Interpolation replaces `{{ server.name }}` and `{{ server.ip }}` with actual values from the SQL result.

---

### Final summary

This YAMLpp program performs a complete data‑driven transformation:

1. Defines an SQL engine (`db`).
2. Queries the database and stores results in `.context.servers`.
3. Iterates over each server row.
4. Interpolates fields into a generated configuration structure.

It is a minimal, declarative ETL pipeline:  
SQL → context → loop → templated output.



