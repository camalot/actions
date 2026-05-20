# Contributing

Thank you for your interest in contributing to this repository! This project is a collection of reusable GitHub Actions. Contributions — new actions, bug fixes, documentation improvements, and tests — are all welcome.

---

## Getting Started

1. **Fork** the repository and clone your fork locally.
2. Create a new branch from `main` with a descriptive name:

   ```bash
   git checkout -b feat/my-new-action
   ```

3. Make your changes, following the conventions described below.
4. Push your branch to your fork and open a Pull Request against `main`.

---

## Repository Structure

Each action lives in its own sub-directory. The top-level directories group actions by category:

``` tree
<category>/
  <action-name>/
    action.yml   # Action definition (inputs, outputs, steps)
    README.md    # Usage documentation for the action
```

For example:

- `version/get/` — calculates the next semantic version using `git-cliff`
- `version/release/` — generates a changelog, commits it, and creates a GitHub Release
- `smells/lint/` — runs Super-Linter across the codebase
- `docs/drjekyll/` — builds and deploys Jekyll documentation

---

## Adding a New Action

1. Choose (or create) an appropriate category directory.
2. Create a sub-directory for your action: `<category>/<action-name>/`.
3. Add `action.yml` — follow the structure of existing actions:
   - Use `composite` as the `runs.using` value.
   - Declare all inputs with clear `description`, `required`, and `default` fields.
   - Declare all outputs with clear `description` and `value` fields.
   - Wrap logical blocks with `::group::`/`::endgroup::` for readable logs.
   - Use `set -euo pipefail` at the top of every `bash` step.
   - Pass sensitive values and GitHub context through `env:` rather than inline expressions.
4. Add a `README.md` documenting inputs, outputs, and a usage example.

---

## Modifying an Existing Action

- Keep changes backwards-compatible wherever possible.
- If an input or output is removed or its behavior changes in a breaking way, note it clearly in the Pull Request description.
- Update the action's `README.md` to reflect any changes.

---

## Commit Message Convention

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) — the format is required because `git-cliff` uses commit messages to generate changelogs and calculate the next semantic version.

```text
<type>(<scope>): <short summary>
```

Common types:

| Type | When to use |
| --- | --- |
| `feat` | A new action or a new feature in an existing action |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `chore` | Maintenance tasks (dependency bumps, CI tweaks) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |

Examples:

```text
feat(version/release): add support for draft releases
fix(smells/lint): pass token via env instead of inline expression
docs(version/get): document all output fields
```

A breaking change must include `BREAKING CHANGE:` in the commit footer, or append `!` after the type:

```text
feat(version/release)!: rename tag_build input to tag_major_minor_build
```

---

## Documentation

Action documentation under `_docs/` is **generated automatically** from each action's `action.yml` via the workflow in `.github/workflows/drjekyll.yml`. You do not need to edit files under `_docs/` manually — update the action's `README.md` and `action.yml` instead.

The docs site is published to [https://camalot.github.io/actions](https://camalot.github.io/actions).

---

## Pull Requests

- Target the `main` branch.
- Keep PRs focused — one action or one fix per PR makes review faster.
- Fill in the PR description explaining *what* changed and *why*.
- Ensure all steps in any modified action run cleanly before opening the PR.
- A maintainer will review and merge your PR once it looks good.
