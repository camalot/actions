# Lint Codebase

Runs [Super-Linter](https://github.com/super-linter/super-linter) across the codebase to enforce code quality and consistency. On pull requests, stale Super-Linter summary comments are automatically removed before each run to keep the PR thread clean.

## How It Works

1. Fetches the full git history (no shallow clone)
2. Loads additional Super-Linter environment variables from a `.env` file (if provided), then falls back to action inputs for any variable not set by the file
3. Finds and deletes any existing Super-Linter summary comment on the pull request (when `delete_previous_comment` is `true`)
4. Runs `super-linter/super-linter/slim` against the codebase
   - By default only changed files are linted (relative to `default_branch`)
   - Files matching `filter_regex_exclude` are skipped
   - Files listed in `.gitignore` are skipped
   - ShellCheck runs with `-x` to follow sourced files, matching local behavior

## Requirements

- Super-Linter linter configuration files (e.g. `.github/linters/`) should be present for languages that require them — see the [Super-Linter documentation](https://github.com/super-linter/super-linter#configure-linters) for details

## Permissions

```yaml
permissions:
  contents: read
  pull-requests: write   # required to post and delete PR comments
```

## Environment Variable Overrides

Every input has a corresponding environment variable. When `super_linter_env_file` is provided, any variable set in that file takes precedence over the matching input. Variables not present in the file fall back to the input value.

| Input | Env var override |
| --- | --- |
| `token` | `GITHUB_TOKEN` (set automatically by GitHub Actions; used directly by Super-Linter and comment steps) |
| `default_branch` | `DEFAULT_BRANCH` |
| `delete_previous_comment` | `DELETE_PREVIOUS_COMMENT` |
| `super_linter_env_file` | `SUPER_LINTER_ENV_FILE` (workflow-level env var; takes precedence over the input) |
| `filter_regex_exclude` | `FILTER_REGEX_EXCLUDE` |
| `validate_all_codebase` | `VALIDATE_ALL_CODEBASE` |

## Inputs

### Optional

| Input | Default | Description |
| --- | --- | --- |
| `token` | `github.token` | GitHub token used for authentication and PR comment management. Defaults to the built-in `GITHUB_TOKEN`. |
| `default_branch` | _(auto-detected)_ | Branch to compare changed files against when `validate_all_codebase` is `false`. Override via `DEFAULT_BRANCH` in `super_linter_env_file`. |
| `delete_previous_comment` | `true` | When `true`, deletes the previous Super-Linter summary comment on a PR before running, avoiding stale comments. Override via `DELETE_PREVIOUS_COMMENT` in `super_linter_env_file`. |
| `super_linter_env_file` | _(none)_ | Path to a `.env` file whose variables are loaded into Super-Linter's environment before it runs. Override via `SUPER_LINTER_ENV_FILE` workflow env var. |
| `filter_regex_exclude` | `(\.devcontainer\|\.github/linters\|docs\|\.vscode)/\|.*/output/\|CHANGELOG\.md` | Regex pattern of files and directories to exclude from linting. Override via `FILTER_REGEX_EXCLUDE` in `super_linter_env_file`. |
| `validate_all_codebase` | `false` | When `true`, lints the entire codebase instead of only files changed relative to `default_branch`. Override via `VALIDATE_ALL_CODEBASE` in `super_linter_env_file`. |

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
```

---

### Lint against a different default branch

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          default_branch: main
```

---

### Validate the entire codebase (e.g. on push to main)

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          validate_all_codebase: 'true'
```

---

### Load extra Super-Linter configuration from a .env file

Variables in the `.env` file take precedence over the matching inputs.

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          super_linter_env_file: .github/linters/super-linter.env
```

---

### Override a variable via the env file

Any of the supported env vars (see table above) can be set in `super_linter_env_file` to override the corresponding input:

```ini
# .github/linters/super-linter.env
FILTER_REGEX_EXCLUDE=(\.devcontainer|\.github/linters|docs|\.vscode|generated)/|.*/output/|CHANGELOG\.md
VALIDATE_ALL_CODEBASE=false
```

---

### Exclude additional paths from linting

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          filter_regex_exclude: '(\.devcontainer|\.github/linters|docs|\.vscode|generated)/|.*/output/|CHANGELOG\.md'
```

---

### Keep stale comments (disable auto-delete)

```yaml
      - uses: camalot/actions/smells/lint@v1
        with:
          delete_previous_comment: 'false'
```
