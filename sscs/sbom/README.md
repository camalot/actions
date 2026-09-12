# SBOM Generation

Generates a Software Bill of Materials (SBOM) using [Syft](https://github.com/anchore/syft), via the official [`anchore/sbom-action`](https://github.com/anchore/sbom-action). Flexible about what gets scanned — a project directory, a single file/archive, or a container image — and defaults to writing the SBOM to a known local path so it can be chained into later steps (e.g. checksummed or attached to a release).

## How It Works

1. Resolves the effective output file: uses `output-file` if set, otherwise defaults to `sbom.json`
2. Runs [`anchore/sbom-action@v0`](https://github.com/anchore/sbom-action), passing through `path` / `file` / `image` and the rest of the inputs unchanged. The underlying action scans with Syft and picks the scan target using `image` > `file` > `path` precedence, so it's safe to leave `path` at its default even when scanning an image or file
3. By default, also uploads the SBOM as a workflow artifact, and as a release asset if the workflow is running during a GitHub release

## Requirements

- The workflow must grant `contents: write` for artifact uploads
- If `upload-release-assets` is `true` (the default), the workflow must also grant `actions: read` so the release step can find the workflow artifact

## Permissions

```yaml
permissions:
  contents: write
  actions: read
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `path` | No | `.` | A path on the filesystem to scan. Mutually exclusive with `file` and `image`. |
| `file` | No | | A file (e.g. an archive) on the filesystem to scan. Mutually exclusive with `path` and `image`. |
| `image` | No | | A container image to scan. Mutually exclusive with `path` and `file`. |
| `registry-username` | No | | Registry username to use when authenticating to an external registry (image scans only). |
| `registry-password` | No | | Registry password to use when authenticating to an external registry (image scans only). |
| `format` | No | `spdx-json` | The SBOM format to export. One of: `spdx`, `spdx-json`, `cyclonedx`, `cyclonedx-json`. |
| `output-file` | No | `sbom.json` | File location to write the resulting SBOM. |
| `artifact-name` | No | | Name to use for the SBOM workflow artifact. Required if using this action more than once in a matrix build. |
| `syft-version` | No | | The version of Syft to use. |
| `dependency-snapshot` | No | `false` | Upload the SBOM to the GitHub Dependency submission API. |
| `upload-artifact` | No | `true` | Upload the SBOM as a workflow artifact. |
| `upload-artifact-retention` | No | `0` | Retention policy (in days) for the uploaded workflow artifact. `0` uses the repository default. |
| `upload-release-assets` | No | `true` | Upload the SBOM as a release asset when run during a GitHub release. |
| `config` | No | | Syft configuration file to use. |
| `github-token` | No | `github.token` | GitHub token used for artifact/release uploads and dependency snapshot submission. |

## Outputs

| Output | Example | Description |
| --- | --- | --- |
| `sbom-file` | `sbom.json` | Path to the generated SBOM file. |

## Examples

### Basic — scan the current project directory

```yaml
jobs:
  sbom:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: read
    steps:
      - uses: actions/checkout@v4

      - id: sbom
        uses: camalot/actions/sscs/sbom@v1

      - run: echo "SBOM written to ${{ steps.sbom.outputs.sbom-file }}"
```

---

### Scan a specific directory

```yaml
      - uses: camalot/actions/sscs/sbom@v1
        with:
          path: ./build/
```

---

### Scan a container image

```yaml
      - uses: camalot/actions/sscs/sbom@v1
        with:
          image: ghcr.io/example/image_name:tag
```

```yaml
      - uses: camalot/actions/sscs/sbom@v1
        with:
          image: my-registry.com/my/image
          registry-username: mr_awesome
          registry-password: ${{ secrets.REGISTRY_PASSWORD }}
```

---

### Scan a single file or archive

```yaml
      - uses: camalot/actions/sscs/sbom@v1
        with:
          file: ./dist/app.tar.gz
```

---

### Use CycloneDX format

```yaml
      - uses: camalot/actions/sscs/sbom@v1
        with:
          format: cyclonedx-json
```

---

### Checksum the generated SBOM alongside other release assets

```yaml
      - id: sbom
        uses: camalot/actions/sscs/sbom@v1
        with:
          path: ./dist/

      - id: checksum
        uses: camalot/actions/sscs/checksum@v1
        with:
          assets: |
            dist/*
            ${{ steps.sbom.outputs.sbom-file }}
```

---

### Matrix build — unique artifact name per job

```yaml
jobs:
  sbom:
    strategy:
      matrix:
        image: [app-linux, app-windows, app-macos]
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: read
    steps:
      - uses: camalot/actions/sscs/sbom@v1
        with:
          image: ghcr.io/example/${{ matrix.image }}:latest
          artifact-name: sbom-${{ matrix.image }}
          output-file: sbom-${{ matrix.image }}.json
```
