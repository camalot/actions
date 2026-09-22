# Test Coverage Report

Collects pre-generated test and coverage report files, runs the
`tests-summary` [`.github/scripts/tests-summary/`] script to produce
Markdown output, writes a GitHub Actions step summary, and optionally posts or
updates a comment on pull requests.

Supports LCOV and Go coverage profiles for coverage, and JUnit XML and
pytest-json-report for test results.

This action is a **post-processing step** — it does not run tests itself.
Pair it with a test-runner action (e.g.
[`smells/test/python/pytest`](./../python/pytest/)) that produces the report
files first.

## How It Works

1. Checks out the full git history (no shallow clone)
2. Sets up Python 3.13 with pip caching
3. Creates an isolated virtual environment and installs the
    `.github/scripts/tests-summary` tool from its `pyproject.toml`
4. Runs `tests-summary` against the supplied report files, writing a detailed
    step-summary Markdown file and a compact PR-comment Markdown file
5. Appends the step summary to `$GITHUB_STEP_SUMMARY`
6. On `pull_request` events: finds any existing comment identified by a
    marker (`<!-- coverage-report -->`, or `<!-- coverage-report:<title> -->`
    when `title` is set) and creates or updates it

## Requirements

- Report files must already exist at the paths supplied via the action inputs
  before this action runs — typically produced by a preceding test-runner step
- A `.github/scripts/tests-summary/` directory with `main.py` and
  `pyproject.toml` must exist in the repository
- The workflow must grant `pull-requests: write` permission when PR comments
  should be posted

## Permissions

```yaml
permissions:
  pull-requests: write   # required to post and update PR comments
```

## Inputs

### Required

| Input | Default | Description |
| --- | --- | --- |
| `lcov-file` | `reports/coverage/lcov.info` | Path to the LCOV coverage file |
| `go-cover-file` | `coverage.out` | Path to the Go coverage profile file |
| `junit-file` | `reports/test/junit.xml` | Path to the JUnit XML test results file |
| `pytest-json-file` | `reports/test/.report.json` | Path to the pytest-json-report file |

### Optional

| Input | Default | Description |
| --- | --- | --- |
| `token` | `${{ github.token }}` | GitHub token used to post or update the PR comment. Defaults to the built-in `GITHUB_TOKEN`. |
| `title` | *(none)* | Optional title appended to the coverage heading, e.g. a matrix job label such as `${{ matrix.os }}`. Also makes the PR comment's identifying marker unique per title, so parallel jobs (e.g. a matrix) each get their own comment instead of overwriting one another's. |

## Examples

### Basic — consume reports from a preceding test step

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: camalot/actions/smells/test/python/pytest@v1

      - uses: camalot/actions/smells/test/coverage@v1
        if: always()
```

---

### Custom report paths

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: |
          pytest \
            --cov --cov-report=lcov:build/coverage/lcov.info \
            --junit-xml=build/test/junit.xml \
            --json-report --json-report-file=build/test/.report.json

      - uses: camalot/actions/smells/test/coverage@v1
        if: always()
        with:
          lcov-file: build/coverage/lcov.info
          junit-file: build/test/junit.xml
          pytest-json-file: build/test/.report.json
```

---

### Go coverage

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: go test -coverprofile=coverage.out ./...

      - uses: camalot/actions/smells/test/coverage@v1
        if: always()
        with:
          go-cover-file: coverage.out
```

---

### Matrix jobs — distinct title and comment per leg

Set `title` so each matrix leg's comment is labeled with the leg it came
from, and so each leg gets its own PR comment instead of overwriting the
others (the title also makes the comment's identifying marker unique).

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    permissions:
      pull-requests: write
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - uses: camalot/actions/smells/test/coverage@v1
        if: always()
        with:
          title: ${{ matrix.os }}
```

---

### Post a PR comment

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: camalot/actions/smells/test/python/pytest@v1

      - uses: camalot/actions/smells/test/coverage@v1
        if: always()
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

---

### Full CI workflow

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

      - uses: camalot/actions/smells/test/coverage@v1
        if: always()
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```
