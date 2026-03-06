# python-semantic-release

A Python implementation of [semantic-release](https://github.com/semantic-release/semantic-release) — automated version management and package publishing driven by conventional commits.

[![Python](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Overview

`python-semantic-release` analyzes your Git commit history using the [Conventional Commits](https://www.conventionalcommits.org/) specification to automatically determine the next version, generate a changelog, tag the release, and publish a GitHub release — all from the command line or a CI pipeline.

## Features

- **Automated versioning** — determines MAJOR, MINOR, or PATCH bumps from commit types
- **Changelog generation** — produces structured Markdown changelogs with compare links
- **GitHub releases** — creates and publishes releases via the GitHub API
- **Version file updates** — writes the new version to `VERSION`, `pyproject.toml`, and any custom files
- **Git commit & tag** — stages changed files, commits, and tags the release
- **Config migration** — converts existing `release.config.js` files to `.releaserc.yaml`
- **CI-aware** — writes `version_changed` to `$GITHUB_OUTPUT` for use in GitHub Actions workflows
- **Configurable rules** — customize which commit types trigger which version bump level

---

## Installation

```bash
pip install python-semantic-release
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add python-semantic-release
```

---

## Quick Start

```bash
# Run a release from the current directory
semantic-release run

# Dry run — preview what would happen without making changes
semantic-release run --dry-run

# Use a specific config file
semantic-release run --config .releaserc.yaml

# Run outside of CI (skip CI environment checks)
semantic-release run --no-ci
```

---

## Commit Convention

This tool follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Default release rules

| Commit type | Version bump |
|-------------|-------------|
| `feat`      | MINOR       |
| `fix`       | PATCH       |
| `perf`      | PATCH       |
| `feat!` / `BREAKING CHANGE:` | MAJOR |
| `chore`, `docs`, `style`, `refactor`, `test`, `ci`, `build` | No release |

### Examples

```
feat: add support for draft releases       → 1.0.0 → 1.1.0
fix(parser): handle empty commit body      → 1.1.0 → 1.1.1
feat!: redesign configuration schema       → 1.1.1 → 2.0.0
chore: update dependencies                 → no release
```

---

## Configuration

Place a `.releaserc.yaml` in your project root:

```yaml
options:
  branches:
    - main
  tag_format: "v${version}"
  dry_run: false

version:
  version_files:
    - VERSION
    - "pyproject.toml:project.version"

commit_analyzer:
  preset: angular
  release_rules:
    - type: feat
      release: minor
    - type: fix
      release: patch
    - type: docs
      release: patch   # promote docs to trigger a release

changelog:
  changelog_file: CHANGELOG.md

git:
  assets:
    - CHANGELOG.md
    - VERSION
    - pyproject.toml
  message: "chore(release): ${nextRelease.version} [skip ci]"

github:
  draft_release: false
  labels:
    - released
```

If no config file is found, sensible defaults are used automatically.

---

## Migrating from `release.config.js`

If your project uses the JavaScript `semantic-release` package, you can convert your existing config:

```bash
semantic-release convert --input release.config.js --output .releaserc.yaml
```

---

## GitHub Actions

```yaml
- name: Semantic Release
  run: semantic-release run --no-ci
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

- name: Check if version changed
  if: env.version_changed == 'true'
  run: echo "A new release was published!"
```

The `version_changed` output variable is written to `$GITHUB_OUTPUT` automatically.

---

## Development

### Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)

### Setup

```bash
git clone https://github.com/jedi-knights/python-semantic-release
cd python-semantic-release
uv sync --extra dev
```

### Running tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

---

## Architecture

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Click command-line interface (`run`, `convert`) |
| `orchestrator.py` | Coordinates the full release pipeline |
| `commit_parser.py` | Parses conventional commits |
| `commit_analyzer.py` | Determines release type from commits |
| `version_service.py` | Calculates and bumps semantic versions |
| `version_updater.py` | Writes new version to files |
| `release_notes_generator.py` | Generates Markdown changelog sections |
| `git_service.py` | Git operations (tag, commit, push) |
| `git_plugin.py` | Stages and commits release assets |
| `github_service.py` | GitHub API client (releases, comments, labels) |
| `config_loader.py` | Loads `.releaserc.yaml` configuration |
| `config_converter.py` | Converts `release.config.js` → `.releaserc.yaml` |
| `models.py` | Shared dataclasses and enums |
| `protocols.py` | Structural typing protocols |

---

## License

MIT
