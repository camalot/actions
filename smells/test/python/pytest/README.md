# PyTest Run Tests

Runs [pytest](https://pytest.org/) with coverage, generates test results and coverage reports, writes a step summary, and optionally posts or updates a comment on pull requests.

## How It Works

1. Checks out the full git history (no shallow clone)
2. Sets up Python 3.13 with pip caching
3. Creates a virtual environment, upgrades pip, and installs the project with its `[dev]` extras
4. Runs `pytest` with `--cov`, writing an lcov coverage report to `reports/coverage/lcov.info`, a JUnit XML report to `reports/test/junit.xml`, and a pytest-json-report to `reports/test/.report.json`
5. Generates a step-summary markdown and a PR-comment markdown from all available reports using `.github/scripts/tests-summary/main.py`
6. Appends the step summary to `$GITHUB_STEP_SUMMARY`
7. On `pull_request` events: finds any existing comment (identified by `<!-- coverage-report -->`) and creates or updates it

## Requirements

- The project must be an installable Python package with a `[dev]` extras group that includes `pytest`, `pytest-cov`, `pytest-json-report`, and any other test dependencies
- A `.github/scripts/tests-summary/main.py` script must exist in the repository for generating the test results and coverage step summary and PR comment
- `pytest` must be configured to collect coverage (e.g. via `pyproject.toml` or `pytest.ini` — the `--cov` flag requires a coverage source to be configured)
- The workflow must grant `pull-requests: write` permission when PR comments should be posted

## Permissions

```yaml
permissions:
  pull-requests: write   # required to post and update coverage PR comments
```

## Inputs

### Optional

| Input | Default | Description |
| --- | --- | --- |
| `token` | `""` | GitHub token used to post or update the coverage comment on pull requests. Required when running on `pull_request` events. |

## Examples

### Basic — run tests and write a step summary

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: camalot/actions/smells/test/python/pytest@v1
```

---

### Post a coverage comment on pull requests

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: camalot/actions/smells/test/python/pytest@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

---

### Run tests as part of a larger CI workflow

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: camalot/actions/smells/test/python/pytest@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```
