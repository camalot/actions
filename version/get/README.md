# Get Next Version

Calculates the next semantic version using [git-cliff](https://git-cliff.org/) based on [Conventional Commits](https://www.conventionalcommits.org/) history since the last tag. Exposes the version in several useful forms — plain and `v`-prefixed, and broken down by major, major.minor, and full major.minor.build components.

## How It Works

1. Fetches the full git history (no shallow clone)
2. Sets up Node.js using the version in `.nvmrc` if present, otherwise defaults to the latest Node.js release
3. Installs `git-cliff` globally
4. Determines the most recent fully-qualified `vMAJOR.MINOR.PATCH` tag as the **current version** — floating tags such as `v1` or `v1.2` are intentionally excluded to prevent an incomplete version from being used as the `git-cliff` base
5. Runs `git-cliff --bumped-version` scoped to `CURRENT_VERSION..HEAD` to derive the **next version** — using an explicit commit range rather than `--unreleased` ensures git-cliff is unaffected by any floating tags sitting at the same commit as the current version
6. Writes all version components to `$GITHUB_OUTPUT` and appends a summary table to `$GITHUB_STEP_SUMMARY`
7. Optionally posts (or updates) a pull-request comment with the same summary table when `enable_pr_comment` is `true` — the comment is identified by an HTML marker (`<!-- version-get-report -->`) so re-runs replace rather than duplicate it

If no prior tags exist, or if `git-cliff` cannot determine a bumped version, the `default_version` input is used as a fallback.

## Requirements

- Commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for `git-cliff` to correctly determine the bump type (`fix` → patch, `feat` → minor, breaking change → major)
- A `.nvmrc` file at the repository root is **optional** — if present, the Node.js version it specifies will be used; otherwise the latest Node.js release is used
- A `cliff.toml` configuration file is recommended for customizing `git-cliff` behavior (optional — `git-cliff` ships with defaults)

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `default_version` | No | `v0.1.0` | Fallback version (with leading `v`) used when no prior tags exist or when `git-cliff` cannot determine a bumped version. |
| `fail_on_default` | No | `false` | When `true`, fails the action if the computed next version equals `default_version` **and** that tag already exists. This guards against silently re-using a stale default when version detection breaks (e.g. shallow clone, no conventional commits). A genuine first release — where the default tag does not yet exist — still succeeds. |
| `fail_on_same_version` | No | `true` | When `true`, fails the action if `next_version` equals `current_version` **and** the full `vMAJOR.MINOR.PATCH` tag already exists. This prevents silently re-tagging an existing release when version detection breaks — the most common cause being a squash-merged PR whose body lines are not parsed as conventional commits. Floating tags (`v1`, `v1.1`) are never checked; only the full patch tag triggers the failure. Set to `false` to suppress the guard. |
| `enable_pr_comment` | No | `false` | When `true`, posts (or updates) a comment on the pull request with the version summary table. Has no effect on non-pull-request events. Can also be enabled by setting the `ENABLE_PR_COMMENT` environment variable to `'true'` at the job or workflow level. |
| `token` | No | `github.token` | GitHub token used to post or update the PR comment. Only required when `enable_pr_comment` is `true`. |

## Environment Variables

| Variable | Description |
| --- | --- |
| `ENABLE_PR_COMMENT` | Set to `'true'` to enable PR comments without changing each action call (equivalent to `enable_pr_comment: 'true'`). |
| `FORCE_NEXT_VERSION` | Pin the next version to an exact value instead of computing it via `git-cliff`. See [Force Next Version](#force-next-version) below. |

## Force Next Version

Setting the `FORCE_NEXT_VERSION` environment variable bypasses `git-cliff` and pins `next_version` to the specified value. All other guards still apply.

**Requirements:**

- Value must match `v?MAJOR.MINOR.PATCH` (e.g. `v1.12.2` or `1.12.2`)
- The full `vMAJOR.MINOR.PATCH` tag must not already exist in the repository — if it does, the action fails with the same error as when `next_version` equals `current_version` and the tag is already present

**Use case:** Skipping a version that cannot be used — for example, when a tag like `v1.12.1` is locked by GitHub and the next intended release must be `v1.12.2`.

## Outputs

| Output | Example | Description |
| --- | --- | --- |
| `current_version` | `1.2.3` | The most recent fully-qualified `vMAJOR.MINOR.PATCH` tag in the repo, without the leading `v`. |
| `next_version` | `1.2.4` | The next version determined by `git-cliff`, without the leading `v`. |
| `major` | `1` | Major component of `next_version`. |
| `major_minor` | `1.2` | Major.Minor of `next_version`. |
| `major_minor_patch` | `1.2.4` | Full Major.Minor.Patch of `next_version`. |
| `tag_major` | `v1` | Major tag form with `v` prefix. |
| `tag_major_minor` | `v1.2` | Major.Minor tag form with `v` prefix. |
| `tag_major_minor_patch` | `v1.2.4` | Full tag form with `v` prefix. |

## Examples

### Basic — print the next version

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - id: version
        uses: camalot/actions/version/get@v1

      - run: echo "Next version is ${{ steps.version.outputs.next_version }}"
```

---

### Fail when version detection falls back to the default

Useful in release pipelines where silently producing `v1.0.0` would be worse than a visible failure.

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: version
        uses: camalot/actions/version/get@v1
        with:
          default_version: 'v1.0.0'
          fail_on_default: 'true'

      - run: echo "Next version is ${{ steps.version.outputs.tag_major_minor_patch }}"
```

---

### Suppress the same-version guard

`fail_on_same_version` defaults to `true`, which fails the action when the computed next version matches the current version and the full patch tag already exists. This catches broken version detection early. If you have a workflow where re-tagging the same version is intentional (e.g. a dry-run or a re-run after a partial failure that already created the tag), you can opt out:

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: version
        uses: camalot/actions/version/get@v1
        with:
          fail_on_same_version: 'false'

      - run: echo "Next version is ${{ steps.version.outputs.tag_major_minor_patch }}"
```

---

### Post a version summary comment on the PR

The comment is created on first run and replaced (not duplicated) on subsequent runs. It has no effect when the workflow is triggered by a non-pull-request event.

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: version
        uses: camalot/actions/version/get@v1
        with:
          enable_pr_comment: 'true'

      - run: echo "Next version is ${{ steps.version.outputs.tag_major_minor_patch }}"
```

You can also enable the comment for all jobs in a workflow without changing each action call by setting the environment variable at the workflow or job level:

```yaml
env:
  ENABLE_PR_COMMENT: 'true'

jobs:
  version:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: version
        uses: camalot/actions/version/get@v1
```

---

### Use a custom fallback version

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - id: version
        uses: camalot/actions/version/get@v1
        with:
          default_version: 'v1.0.0'

      - run: echo "Next version is ${{ steps.version.outputs.tag_major_minor_patch }}"
```

---

### Tag a release after computing the version

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - id: version
        uses: camalot/actions/version/get@v1

      - name: Create and push tag
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git tag "${{ steps.version.outputs.tag_major_minor_patch }}"
          git push origin "${{ steps.version.outputs.tag_major_minor_patch }}"
```

---

### Pass the version to a downstream job

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    outputs:
      tag: ${{ steps.version.outputs.tag_major_minor_patch }}
    steps:
      - id: version
        uses: camalot/actions/version/get@v1

  build:
    needs: version
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: |
          docker build -t myapp:${{ needs.version.outputs.tag }} .
```

---

### Force a specific next version

Use `FORCE_NEXT_VERSION` when you need to skip a version — for example, if `v1.12.1` is locked and cannot be created, and the next release must be `v1.12.2`.

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    env:
      FORCE_NEXT_VERSION: 'v1.12.2'
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: version
        uses: camalot/actions/version/get@v1

      - run: echo "Next version is ${{ steps.version.outputs.tag_major_minor_patch }}"
```

The value may include or omit the leading `v`. The action fails if the tag already exists in the repository.

---

### Use floating major tag for Docker image labelling

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - id: version
        uses: camalot/actions/version/get@v1

      - name: Build and push image
        run: |
          docker build \
            -t myapp:${{ steps.version.outputs.tag_major_minor_patch }} \
            -t myapp:${{ steps.version.outputs.tag_major_minor }} \
            -t myapp:${{ steps.version.outputs.tag_major }} \
            -t myapp:latest \
            .
```
