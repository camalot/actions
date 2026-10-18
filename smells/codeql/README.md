# CodeQL Analysis

This directory contains the CodeQL analysis setup for the project, including the TaskFile for running CodeQL queries and analyzing the codebase for potential security vulnerabilities and code quality issues.

## Action

### Permissions

```yaml
permissions:
  # required for all workflows
  security-events: write

  # required to fetch internal or private CodeQL packs
  packages: read

  # only required for workflows in private repositories
  actions: read
  contents: read
```

### Inputs

The following inputs are available for the CodeQL action:

- `language`: The programming language to analyze (e.g., `javascript`, `python`, `cpp`).
- `build-mode`: The build mode for the analysis (e.g., `none`, `incremental`).

### Example

``` yaml
name: "CodeQL Advanced"

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '25 9 * * 0'

jobs:
  analyze:
    name: Analyze (${{ matrix.language }})
    runs-on: ${{ (matrix.language == 'swift' && 'macos-latest') || 'ubuntu-latest' }}
    permissions:
      security-events: write
      packages: read
      actions: read
      contents: read

    strategy:
      fail-fast: false
      matrix:
        include:
        - language: actions
          build-mode: none
        - language: javascript
          build-mode: none
    steps:
    - uses: actions/checkout@v7
      with:
        fetch-depth: 0
        persist-credentials: false

    - name: CodeQL Analysis ${{ matrix.language }}
      uses: camalot/actions/smells/codeql@v1
      with:
        language: ${{ matrix.language }}
        build-mode: ${{ matrix.build-mode }}
```

## TaskFile

The TaskFile defines tasks for running CodeQL analysis, including creating the database, analyzing the code, and reporting any findings. It is used to automate the CodeQL workflow within the project.

### Include

To include the CodeQL analysis tasks in your project, you need to reference the TaskFile in your build or automation setup. This ensures that the tasks defined for creating the database, running queries, and reporting results are available for execution.

```yaml
---

version: '3'

includes:
  codeql: 
    # https
    # taskfile: https://github.com/camalot/actions/raw/refs/heads/main/smells/codeql/TaskFile.yml
    # git over ssh
    # taskfile: 'git@github.com:camalot/actions.git//smells/codeql/TaskFile.yml?ref=main'
    # git over https
    taskfile: https://github.com/camalot/actions.git//smells/codeql/TaskFile.yml?ref=main
    flatten: true

```

> [!IMPORTANT]
> If you are running the task in a non-interactive environment, make sure to trust the necessary hosts by configuring the `trusted-hosts` section in your `.taskrc.yml` file.

``` yaml
---

remote:
  trusted-hosts:
    - github.com

```

> [!NOTE]
> If you use `git over SSH` or `git over HTTPS` for including the TaskFile, you may need to use a `.taskrc.yml` file to set the cache and temp directories for Taskfile execution.

``` yaml
---

remote:
  trusted-hosts:
    - github.com
  cache-dir: .task
temp-dir: .task
```

### Tasks

The TaskFile includes tasks such as `codeql:*:*` for running CodeQL analysis on different parts of the project. These tasks handle the creation of the CodeQL database, execution of queries, and reporting of any alerts found during the analysis.

There are 2 arguments for the `codeql:*:*` task:

- `LANGUAGE`: The programming language to analyze (e.g., `javascript`, `python`, `cpp`).
- `SOURCE_ROOT`: The root directory of the source code to analyze.

### Example Usage

```yaml
---

version: '3'

includes:
  codeql-remote: 
    taskfile: 'git@github.com:camalot/actions.git//smells/codeql/TaskFile.yml?ref=main'
    flatten: true


  codeql:
    cmds:
      - task: codeql:actions:.
      - task: codeql:javascript:src

```
