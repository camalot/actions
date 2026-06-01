# Release Version

Generates the changelog via [git-cliff](https://git-cliff.org/), commits and pushes it, creates or moves the supplied semver tags, and creates a GitHub Release — all in one step. The release body contains only the changelog entries for the new version.

## How It Works

1. Fetches the full git history with credentials retained so `git push` is authenticated
2. Sets up Node.js using the version in `.nvmrc` if present, otherwise defaults to the latest Node.js release
3. Installs `git-cliff` globally
4. Configures the git commit author using the supplied `git_user_name` / `git_user_email` inputs
5. Renders the release notes for this version only (using `--unreleased --strip header`) and saves them to a temp file
6. Captures the pre-release state (the prior remote targets of the floating `tag_major` / `tag_major_minor` tags) **before anything is mutated**, so the changes can be rolled back if a later step fails
7. Prepends the new version section to `CHANGELOG.md` (or the configured `changelog_file`)
8. Updates any version files that exist in the repo (`.version`, `Chart.yaml`, Jekyll `_config.yml`)
9. Commits the changelog and version file changes and pushes to the current branch
10. Deletes any existing local and remote copies of the three supplied tags, then recreates and pushes them pointing at the new commit (floating major and major.minor tags are moved automatically)
11. Deletes any existing GitHub Release for the tag and creates a fresh one with the rendered notes
12. If any of the above steps fail, [rolls back](#rollback-on-failure) the pushed changes in reverse order
13. Appends a summary table to `$GITHUB_STEP_SUMMARY`

## Rollback on Failure

The action captures the relevant state **before** it mutates anything, then performs an **atomic rollback** if any step within the action fails. The rollback undoes whatever was already pushed, in reverse order:

1. **GitHub Release** — deletes the release for `tag_major_minor_patch` (no-op if one was never created).
2. **Tags** — only when tag mutation had begun:
    - The patch tag (`tag_major_minor_patch`) is brand-new for this release, so it is **deleted**.
    - The floating tags (`tag_major`, `tag_major_minor`) are **restored** to the remote targets captured before the release. If a floating tag did not exist before this release, it is **deleted** instead.
3. **Release commit** — if the changelog/version commit was pushed, it is undone with `git revert` (not a force-push), so it works under branch protection rules that forbid rewriting history. The revert is committed and pushed to the current branch.

> [!NOTE]
> The rollback only fires on failures that occur **within this action**. It cannot detect a failure in a step that runs *after* this action in the calling workflow. Gate any such follow-up steps (e.g. a marketplace publish) on [`success()`](https://docs.github.com/en/actions/learn-github-actions/expressions#success) so they skip when the release fails.

## Requirements

- Commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification so `git-cliff` can generate meaningful changelog entries
- A `.nvmrc` file at the repository root is **optional** — if present, the Node.js version it specifies will be used; otherwise the latest Node.js release is used
- A `cliff.toml` configuration file is recommended for customising `git-cliff` behaviour (optional — `git-cliff` ships with defaults)
- The workflow must grant `contents: write` permission so the action can push commits, tags, and create releases
- `yq` must be available on the runner if you use `chart_version_file` or `jekyll_config_file` updates (`yq` is pre-installed on `ubuntu-latest`)

## Permissions

```yaml
permissions:
  contents: write
```

## Inputs

### Required

| Input | Description |
| --- | --- |
| `tag_major` | Major tag form, e.g. `v1`. Created and moved to point at the new commit. |
| `tag_major_minor` | Major.Minor tag form, e.g. `v1.2`. Created and moved to point at the new commit. |
| `tag_major_minor_patch` | Full Major.Minor.Patch tag, e.g. `v1.2.3`. Used as the GitHub Release tag. |

### Optional

| Input | Default | Description |
| --- | --- | --- |
| `prerelease` | `false` | When `true`, mark the GitHub Release as a prerelease. |
| `draft` | `false` | When `true`, create the GitHub Release as a draft. |
| `token` | `github.token` | GitHub token used for `git-cliff` PR metadata lookups and creating the GitHub Release. |

> [!WARNING]
> The following inputs are **DEPRECATED** and will be removed in a future major release. Please use the corresponding environment variables instead.

| Input | Default | Description |
| --- | --- | --- |
| `changelog_file` | `CHANGELOG.md` | Path (relative to repo root) of the changelog file to update. |
| `git_user_name` | `github-actions[bot]` | Author name for the changelog commit. |
| `git_user_email` | `41898282+github-actions[bot]@users.noreply.github.com` | Author email for the changelog commit. |
| `chart_version_file` | `chart/Chart.yaml` | [**DEPRECATED**] Path to a `Chart.yaml` file whose `version` and `appVersion` fields are updated to the new version. Skipped if the file does not exist. |
| `chart_app_version_file` | `` | [**DEPRECATED**] Path to a `Chart.yaml` file whose `appVersion` field is updated to match the new version. Skipped if the file does not exist. |
| `jekyll_config_file` | `docs/_config.yml` | [**DEPRECATED**] Path to a Jekyll `_config.yml` file whose `version` field is updated to the new version. Skipped if the file does not exist. |

### Environment Variables

The following environment variables **SHOULD** be used instead of the corresponding inputs as the inputs are deprecated.

> [!NOTE]
> If both the input and environment variable are set, the input takes precedence.

| Environment Variable | Default | Description |
| --- | --- | --- |
| `GIT_USER_NAME` | `github-actions[bot]` | Author name for the changelog commit. |
| `GIT_USER_EMAIL` | `41898282+github-actions[bot]@users.noreply.github.com` | Author email for the changelog commit. |
| `UPDATE_FILE_CHANGELOG` | `CHANGELOG.md` | Path (relative to repo root) of the changelog files to update. |
| `UPDATE_FILE_CHART_VERSION` | `chart/Chart.yaml` | Comma-separated paths to `Chart.yaml` files whose `version` field is updated to the new version. |
| `UPDATE_FILE_CHART_APP_VERSION` | `` | Comma-separated paths to `Chart.yaml` files whose `appVersion` field is updated to the new version. |
| `UPDATE_FILE_JEKYLL_CONFIG` | `docs/_config.yml` | Comma-separated paths to Jekyll `_config.yml` files whose `version` field is updated to the new version. |
| `UPDATE_FILE_PACKAGE_JSON` | `package.json` | Comma-separated paths to `package.json` files whose `version` field is updated to the new version. |

## Outputs

| Output | Description |
| --- | --- |
| `release_notes_file` | Path to the rendered release-notes file (only the new version section). |
| `release_url` | URL of the created GitHub Release. |

## Examples

### Typical release workflow — compute version then release

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - id: version
        uses: camalot/actions/version/get@v1

      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             {% raw %}${{ steps.version.outputs.tag_major }}{% endraw %}
          tag_major_minor:       {% raw %}${{ steps.version.outputs.tag_major_minor }}{% endraw %}
          tag_major_minor_patch: {% raw %}${{ steps.version.outputs.tag_major_minor_patch }}{% endraw %}
```

---

### Create a prerelease

```yaml
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             {% raw %}${{ steps.version.outputs.tag_major }}{% endraw %}
          tag_major_minor:       {% raw %}${{ steps.version.outputs.tag_major_minor }}{% endraw %}
          tag_major_minor_patch: {% raw %}${{ steps.version.outputs.tag_major_minor_patch }}{% endraw %}
          prerelease: 'true'
```

---

### Create a draft release for review before publishing

```yaml
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             {% raw %}${{ steps.version.outputs.tag_major }}{% endraw %}
          tag_major_minor:       {% raw %}${{ steps.version.outputs.tag_major_minor }}{% endraw %}
          tag_major_minor_patch: {% raw %}${{ steps.version.outputs.tag_major_minor_patch }}{% endraw %}
          draft: 'true'
```

---

### Use a custom changelog path and git author

```yaml
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             {% raw %}${{ steps.version.outputs.tag_major }}{% endraw %}
          tag_major_minor:       {% raw %}${{ steps.version.outputs.tag_major_minor }}{% endraw %}
          tag_major_minor_patch: {% raw %}${{ steps.version.outputs.tag_major_minor_patch }}{% endraw %}
          changelog_file: 'docs/CHANGELOG.md'
          git_user_name:  'release-bot'
          git_user_email: 'release-bot@example.com'
```

---

### Two-job pipeline — version in one job, release in another

```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    outputs:
      tag_major:             {% raw %}${{ steps.v.outputs.tag_major }}{% endraw %}
      tag_major_minor:       {% raw %}${{ steps.v.outputs.tag_major_minor }}{% endraw %}
      tag_major_minor_patch: {% raw %}${{ steps.v.outputs.tag_major_minor_patch }}{% endraw %}
    steps:
      - id: v
        uses: camalot/actions/version/get@v1

  release:
    needs: version
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             {% raw %}${{ needs.version.outputs.tag_major }}{% endraw %}
          tag_major_minor:       {% raw %}${{ needs.version.outputs.tag_major_minor }}{% endraw %}
          tag_major_minor_patch: {% raw %}${{ needs.version.outputs.tag_major_minor_patch }}{% endraw %}
```

---

### Use the release URL in a subsequent step

```yaml
      - id: release
        uses: camalot/actions/version/release@v1
        with:
          tag_major:             {% raw %}${{ steps.version.outputs.tag_major }}{% endraw %}
          tag_major_minor:       {% raw %}${{ steps.version.outputs.tag_major_minor }}{% endraw %}
          tag_major_minor_patch: {% raw %}${{ steps.version.outputs.tag_major_minor_patch }}{% endraw %}

      - run: echo "Published to {% raw %}${{ steps.release.outputs.release_url }}{% endraw %}"
```
