
Runs [Super-Linter](https://github.com/super-linter/super-linter) across the codebase to enforce code quality and consistency. On pull requests, stale Super-Linter summary comments are automatically removed before each run to keep the PR thread clean.

## How It Works

1. Fetches the full git history (no shallow clone)
2. Optionally loads additional Super-Linter environment variables from a `.env` file
3. Finds and deletes any existing Super-Linter summary comment on the pull request (when `delete_previous_comment` is `true`)
4. Runs `super-linter/super-linter/slim` against the codebase
   - By default only changed files are linted (relative to `default_branch`)
   - Files matching `filter_regex_exclude` are skipped
   - Files listed in `.gitignore` are skipped
   - ShellCheck runs with `-x` to follow sourced files, matching local behavior

## Requirements

- A GitHub token with permission to read the repository and post/delete PR comments
- Super-Linter linter configuration files (e.g. `.github/linters/`) should be present for languages that require them — see the [Super-Linter documentation](https://github.com/super-linter/super-linter#configure-linters) for details

## Permissions

```yaml
permissions:
  contents: read
  pull-requests: write   # required to post and delete PR comments
```

## Inputs

### Required

| Input | Description |
| --- | --- |
| `token` | GitHub token used for authentication and PR comment management. |

### Optional

| Input | Default | Description |
| --- | --- | --- |
| `default_branch` | `main` | Branch to compare changed files against when `validate_all_codebase` is `false`. |
| `delete_previous_comment` | `true` | When `true`, deletes the previous Super-Linter summary comment on a PR before running, avoiding stale comments. |
| `super_linter_env_file` | _(none)_ | Path to a `.env` file whose variables are loaded into Super-Linter's environment before it runs. |
| `filter_regex_exclude` | `(\.devcontainer\|\.github/linters\|docs\|\.vscode)/\|.*/output/\|CHANGELOG\.md)` | Regex pattern of files and directories to exclude from linting. |
| `validate_all_codebase` | `false` | When `true`, lints the entire codebase instead of only files changed relative to `default_branch`. |

## Examples

### Basic — lint changed files on a pull request

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

---

### Lint against a different default branch

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          default_branch: main
```

---

### Validate the entire codebase (e.g. on push to main)

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          validate_all_codebase: 'true'
```

---

### Load extra Super-Linter configuration from a .env file

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          super_linter_env_file: .github/linters/super-linter.env
```

---

### Exclude additional paths from linting

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          filter_regex_exclude: '(\.devcontainer|\.github/linters|docs|\.vscode|generated)/|.*/output/|CHANGELOG\.md'
```

---

### Keep stale comments (disable auto-delete)

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          delete_previous_comment: 'false'
```
