# Get Next Version

Calculates the next semantic version using [git-cliff](https://git-cliff.org/) based on [Conventional Commits](https://www.conventionalcommits.org/) history since the last tag. Exposes the version in several useful forms — plain and `v`-prefixed, and broken down by major, major.minor, and full major.minor.build components.

## How It Works

1. Fetches the full git history (no shallow clone)
2. Sets up Node.js using the version in `.nvmrc` if present, otherwise defaults to the latest Node.js release
3. Installs `git-cliff` globally
4. Determines the most recent `v*` tag as the **current version**
5. Runs `git-cliff --bumped-version` against unreleased commits to derive the **next version**
6. Writes all version components to `$GITHUB_OUTPUT` and appends a summary table to `$GITHUB_STEP_SUMMARY`

If no prior tags exist, or if `git-cliff` cannot determine a bumped version, the `default_version` input is used as a fallback.

## Requirements

- Commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for `git-cliff` to correctly determine the bump type (`fix` → patch, `feat` → minor, breaking change → major)
- A `.nvmrc` file at the repository root is **optional** — if present, the Node.js version it specifies will be used; otherwise the latest Node.js release is used
- A `cliff.toml` configuration file is recommended for customizing `git-cliff` behavior (optional — `git-cliff` ships with defaults)

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `default_version` | No | `v0.1.0` | Fallback version (with leading `v`) used when no prior tags exist or when `git-cliff` cannot determine a bumped version. |

## Outputs

| Output | Example | Description |
| --- | --- | --- |
| `current_version` | `1.2.3` | The most recent `v*` tag in the repo, without the leading `v`. |
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
