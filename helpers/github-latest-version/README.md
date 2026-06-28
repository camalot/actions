# GitHub Latest Version

Queries the GitHub API to retrieve the latest release version of any repository. Falls back to the most recent tag if the repository has no releases. The `v` prefix is stripped from the returned version.

## How It Works

1. Calls the GitHub Releases API (`/releases/latest`) for the given repository
2. If no release exists, falls back to the Tags API (`/tags`) and takes the most recent tag
3. Strips the leading `v` prefix from the version string if present
4. Writes the version to `$GITHUB_OUTPUT`

## Inputs

### Required

| Input | Description |
| --- | --- |
| `organization` | GitHub organization or user that owns the repository. |
| `repository` | Repository name to look up the latest version for. |

### Optional

| Input | Default | Description |
| --- | --- | --- |
| `token` | `github.token` | GitHub token for authentication. Defaults to the built-in `GITHUB_TOKEN`. |

## Outputs

| Output | Example | Description |
| --- | --- | --- |
| `version` | `4.44.3` | Latest release or tag version, with the leading `v` stripped. |

## Examples

### Basic — get the latest version of a repository

```yaml
jobs:
  example:
    runs-on: ubuntu-latest
    steps:
      - id: version
        uses: camalot/actions/helpers/github-latest-version@v1
        with:
          organization: mikefarah
          repository: yq

      - run: echo "Latest yq version is ${{ steps.version.outputs.version }}"
```

---

### Use the version to install a tool

```yaml
jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - id: yq-version
        uses: camalot/actions/helpers/github-latest-version@v1
        with:
          organization: mikefarah
          repository: yq

      - uses: chrisdickinson/setup-yq@latest
        with:
          yq-version: v${{ steps.yq-version.outputs.version }}
```

---

### Use a custom token for private repositories or higher rate limits

```yaml
      - id: version
        uses: camalot/actions/helpers/github-latest-version@v1
        with:
          organization: my-org
          repository: my-private-repo
          token: ${{ secrets.MY_PAT }}
```
