
See [DrJekyll Action](https://camalot.github.io/drjekyll-action) for documentation on how to use this action to publish documentation to GitHub Pages using DrJekyll.

## Quick Start

- Enable GitHub Pages in your repository settings (source: GitHub Actions).
  `Repository settings > Pages > Source > GitHub Actions`
- Add a `docs/` directory with an `index.md` and a `_config.yml` file. The `_config.yml` should have at least the following content:

  ```yaml
  ---
  title: "My Project Documentation"
  description: "Documentation for My Project"
  ```

- Create `.github/workflows/drjekyll.yml` workflow file with the following content:

  ```yaml
  name: Publish Documentation

  on: # yamllint disable-line rule:truthy
    workflow_dispatch:
  permissions: {}
  jobs:
    publish:
      permissions:
        contents: write
        pages: write
        statuses: write
        id-token: write
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v6
          with:
            fetch-depth: 0
            persist-credentials: false

        - name: Publish with DrJekyll
          uses: camalot/actions/docs/drjekyll@main
          with:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
            input_dir: './docs'
            output_dir: './_site'
  ```

- Trigger the workflow from the Actions tab.
