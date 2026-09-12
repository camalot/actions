# Checksum Generation

Generates a checksum file for CI pipeline assets — local build outputs matched by glob, and optionally artifacts uploaded elsewhere in the current workflow run. Produces a single `checksum.txt` (GNU coreutils format) that can be verified with `sha256sum -c` and attached to a release alongside the assets it covers.

## How It Works

1. Validates the `algorithm` input against the supported set (`sha256`, `sha384`, `sha512`, `sha1`, `md5`) and confirms the corresponding `*sum` tool is available on the runner
2. If `download-artifacts` is `true`, downloads artifacts uploaded (via `actions/upload-artifact`) elsewhere in the current workflow run into `artifacts-path`, using `gh run download`
3. Expands the glob pattern(s) in `assets` (one per line, `**` supported for recursive matches) and combines them with any downloaded artifact files, de-duplicating by real path
4. Fails with a clear error if no files matched
5. Hashes each file in text mode and appends `<hash>  <filename>` (two spaces, no path — just the basename) to the checksum file
6. Writes `checksum-file` and `count` outputs, and appends a summary table to `$GITHUB_STEP_SUMMARY`

> [!NOTE]
> Only the basename of each asset is recorded in the checksum file, not its directory path. This matches how release assets are actually laid out — GitHub flattens all assets into a single directory on a release — so `sha256sum -c checksum.txt` works correctly once the assets and `checksum.txt` are downloaded together.

## Requirements

- `gh` (GitHub CLI) must be available on the runner if `download-artifacts` is `true` (pre-installed on `ubuntu-latest`)
- The workflow must grant `actions: read` permission if `download-artifacts` is `true`, so `gh run download` can list and fetch artifacts

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `assets` | Yes | `*` | Glob pattern(s) of local files to checksum, one per line (e.g. `dist/*.zip`). Supports `**` for recursive matching. |
| `algorithm` | No | `sha256` | The algorithm to use for generating the checksum (case-insensitive). One of: `sha256`, `sha384`, `sha512`, `sha1`, `md5`. |
| `checksum-file` | No | `checksum.txt` | The file to which the generated checksum will be written. |
| `download-artifacts` | No | `false` | When `true`, also downloads artifacts uploaded via `actions/upload-artifact` elsewhere in the current workflow run and includes them in the checksum. |
| `artifacts-path` | No | `artifacts` | Directory to download workflow run artifacts into. Only used when `download-artifacts` is `true`. |
| `artifact-pattern` | No | `*` | Glob pattern filtering which workflow run artifacts to download. Only used when `download-artifacts` is `true`. |
| `run-id` | No | `github.run_id` | The workflow run ID to download artifacts from. Only used when `download-artifacts` is `true`. |
| `token` | No | `github.token` | GitHub token used to download workflow run artifacts. Only used when `download-artifacts` is `true`. |

## Outputs

| Output | Example | Description |
| --- | --- | --- |
| `checksum-file` | `checksum.txt` | Path to the generated checksum file. |
| `count` | `4` | Number of assets checksummed. |

## Examples

### Basic — checksum local build output

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: ./build.sh # produces files under dist/

      - id: checksum
        uses: camalot/actions/sscs/checksum@v1
        with:
          assets: 'dist/*'

      - run: echo "Wrote ${{ steps.checksum.outputs.count }} checksums to ${{ steps.checksum.outputs.checksum-file }}"
```

---

### Multiple glob patterns

```yaml
      - uses: camalot/actions/sscs/checksum@v1
        with:
          assets: |
            dist/*.zip
            dist/*.tar.gz
```

---

### Use a different algorithm

```yaml
      - uses: camalot/actions/sscs/checksum@v1
        with:
          assets: 'dist/*'
          algorithm: 'sha512'
```

---

### Include artifacts uploaded by other jobs in the same workflow run

Useful when several jobs each build and upload a platform-specific asset, and a final job needs to checksum everything together before creating a release.

```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [linux, windows, macos]
    runs-on: ubuntu-latest
    steps:
      - run: ./build.sh ${{ matrix.os }}

      - uses: actions/upload-artifact@v4
        with:
          name: app-${{ matrix.os }}
          path: dist/app-${{ matrix.os }}*

  checksum-and-release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: write
    steps:
      - id: checksum
        uses: camalot/actions/sscs/checksum@v1
        with:
          assets: '' # no local assets in this job — everything comes from artifacts
          download-artifacts: 'true'

      - uses: softprops/action-gh-release@v2
        with:
          files: |
            artifacts/**/*
            ${{ steps.checksum.outputs.checksum-file }}
```

---

### Filter which workflow run artifacts get downloaded

```yaml
      - uses: camalot/actions/sscs/checksum@v1
        with:
          download-artifacts: 'true'
          artifact-pattern: 'app-*'
```
