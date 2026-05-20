# Release Version

Generates the changelog via [git-cliff](https://git-cliff.org/), commits and pushes it, creates or moves the supplied semver tags, and creates a GitHub Release — all in one step. The release body contains only the changelog entries for the new version.

## How It Works

1. Fetches the full git history with credentials retained so `git push` is authenticated
2. Sets up Node.js using the version in `.nvmrc` if present, otherwise defaults to the latest Node.js release
3. Installs `git-cliff` globally
4. Configures the git commit author using the supplied `git_user_name` / `git_user_email` inputs
5. Renders the release notes for this version only (using `--unreleased --strip header`) and saves them to a temp file
6. Prepends the new version section to `CHANGELOG.md` (or the configured `changelog_file`)
7. Updates any version files that exist in the repo (`.version`, `Chart.yaml`, Jekyll `_config.yml`)
8. Commits the changelog and version file changes and pushes to the current branch
9. Deletes any existing local and remote copies of the three supplied tags, then recreates and pushes them pointing at the new commit (floating major and major.minor tags are moved automatically)
10. Deletes any existing GitHub Release for the tag and creates a fresh one with the rendered notes
11. Appends a summary table to `$GITHUB_STEP_SUMMARY`

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
|---|---|
| `tag_major` | Major tag form, e.g. `v1`. Created and moved to point at the new commit. |
| `tag_major_minor` | Major.Minor tag form, e.g. `v1.2`. Created and moved to point at the new commit. |
| `tag_major_minor_build` | Full Major.Minor.Build tag, e.g. `v1.2.3`. Used as the GitHub Release tag. |

### Optional

| Input | Default | Description |
|---|---|---|
| `changelog_file` | `CHANGELOG.md` | Path (relative to repo root) of the changelog file to update. |
| `prerelease` | `false` | When `true`, mark the GitHub Release as a prerelease. |
| `draft` | `false` | When `true`, create the GitHub Release as a draft. |
| `token` | `github.token` | GitHub token used for `git-cliff` PR metadata lookups and creating the GitHub Release. |
| `git_user_name` | `github-actions[bot]` | Author name for the changelog commit. |
| `git_user_email` | `github-actions[bot]@users.noreply.github.com` | Author email for the changelog commit. |
| `chart_version_file` | `chart/Chart.yaml` | Path to a `Chart.yaml` file whose `version` and `appVersion` fields are updated to the new version. Skipped if the file does not exist. |
| `jekyll_config_file` | `docs/_config.yml` | Path to a Jekyll `_config.yml` file whose `version` field is updated to the new version. Skipped if the file does not exist. |

## Outputs

| Output | Description |
|---|---|
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
          tag_major:             ${{ steps.version.outputs.tag_major }}
          tag_major_minor:       ${{ steps.version.outputs.tag_major_minor }}
          tag_major_minor_build: ${{ steps.version.outputs.tag_major_minor_build }}
```

---

### Create a prerelease

```yaml
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             ${{ steps.version.outputs.tag_major }}
          tag_major_minor:       ${{ steps.version.outputs.tag_major_minor }}
          tag_major_minor_build: ${{ steps.version.outputs.tag_major_minor_build }}
          prerelease: 'true'
```

---

### Create a draft release for review before publishing

```yaml
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             ${{ steps.version.outputs.tag_major }}
          tag_major_minor:       ${{ steps.version.outputs.tag_major_minor }}
          tag_major_minor_build: ${{ steps.version.outputs.tag_major_minor_build }}
          draft: 'true'
```

---

### Use a custom changelog path and git author

```yaml
      - uses: camalot/actions/version/release@v1
        with:
          tag_major:             ${{ steps.version.outputs.tag_major }}
          tag_major_minor:       ${{ steps.version.outputs.tag_major_minor }}
          tag_major_minor_build: ${{ steps.version.outputs.tag_major_minor_build }}
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
      tag_major:             ${{ steps.v.outputs.tag_major }}
      tag_major_minor:       ${{ steps.v.outputs.tag_major_minor }}
      tag_major_minor_build: ${{ steps.v.outputs.tag_major_minor_build }}
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
          tag_major:             ${{ needs.version.outputs.tag_major }}
          tag_major_minor:       ${{ needs.version.outputs.tag_major_minor }}
          tag_major_minor_build: ${{ needs.version.outputs.tag_major_minor_build }}
```

---

### Use the release URL in a subsequent step

```yaml
      - id: release
        uses: camalot/actions/version/release@v1
        with:
          tag_major:             ${{ steps.version.outputs.tag_major }}
          tag_major_minor:       ${{ steps.version.outputs.tag_major_minor }}
          tag_major_minor_build: ${{ steps.version.outputs.tag_major_minor_build }}

      - run: echo "Published to ${{ steps.release.outputs.release_url }}"
```
