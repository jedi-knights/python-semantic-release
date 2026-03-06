import os
from pathlib import Path
from typing import Any

import click

from python_semantic_release.config_converter import ConfigConverter
from python_semantic_release.config_loader import ConfigLoader
from python_semantic_release.models import ReleaseRule
from python_semantic_release.orchestrator import (
    SemanticReleaseConfig,
    SemanticReleaseOrchestrator,
)

_DEFAULT_RULES = [
    ReleaseRule(type="feat", release="minor"),
    ReleaseRule(type="fix", release="patch"),
    ReleaseRule(type="perf", release="patch"),
    ReleaseRule(type="build", release=None),
    ReleaseRule(type="chore", release=None),
    ReleaseRule(type="ci", release=None),
    ReleaseRule(type="docs", release=None),
    ReleaseRule(type="style", release=None),
    ReleaseRule(type="refactor", release=None),
    ReleaseRule(type="test", release=None),
]

_RELEASE_EXPLANATIONS: dict[str, str] = {
    "major": "  -> Breaking changes detected - MAJOR version bump",
    "minor": "  -> New features added - MINOR version bump",
    "patch": "  -> Bug fixes or improvements - PATCH version bump",
}


def _default_config() -> SemanticReleaseConfig:
    config = SemanticReleaseConfig()
    config.commit_analyzer.release_rules = list(_DEFAULT_RULES)
    return config


def _load_config(config_path: Path | None) -> SemanticReleaseConfig:
    if config_path:
        return ConfigLoader(config_path).load()
    default = Path.cwd() / ".releaserc.yaml"
    if default.exists():
        return ConfigLoader(default).load()
    return _default_config()


def _format_note_line(line: str) -> str | None:
    if not line.strip() or line.startswith("#"):
        return None
    if line.startswith("*"):
        return f"    {line}"
    if line.startswith("###"):
        return f"    {line.replace('###', '').strip()}:"
    return f"    {line}"


def _print_notes(notes: str) -> None:
    note_lines = notes.split("\n")
    display_lines: list[str] = []
    for line in note_lines[:20]:
        formatted = _format_note_line(line)
        if formatted is not None:
            display_lines.append(formatted)
    for line in display_lines[:15]:
        click.echo(line)
    if len(note_lines) > 20:
        click.echo("    ...")
    click.echo()


def _print_release_result(result: Any, orchestrator: Any) -> None:
    type_display = ""
    explanation = ""
    if result.type:
        type_display = f" ({result.type.value.upper()})"
        explanation = _RELEASE_EXPLANATIONS.get(result.type.value, "")
    click.echo(f"Release Published{type_display}")
    click.echo("=" * 80)
    last_tag = orchestrator.git_service.get_last_tag()
    if last_tag:
        click.echo(f"  Previous: {last_tag.lstrip('v')}")
        click.echo(f"  New:      {result.version}")
        if explanation:
            click.echo(explanation)
    else:
        click.echo(f"  Version:  {result.version} (initial release)")
    click.echo(f"  Tag:      {result.git_tag}")
    click.echo(f"  Commit:   {result.git_head}")
    if result.url:
        click.echo(f"  URL:      {result.url}")
    click.echo()
    if result.notes:
        click.echo("  Changes in this release:")
        click.echo()
        _print_notes(result.notes)
    click.echo("Version bump: YES")
    click.echo("=" * 80)


def _print_no_release_result(orchestrator: Any) -> None:
    click.echo("No Release Needed")
    click.echo("=" * 80)
    last_tag = orchestrator.git_service.get_last_tag()
    if last_tag:
        click.echo(f"  Current version: {last_tag.lstrip('v')}")
    click.echo()
    click.echo("  Why no release?")
    click.echo("  * No commits found that require a version bump")
    click.echo(
        "  * Version bumps require: feat (minor), fix (patch), or breaking changes (major)"
    )
    click.echo(
        "  * Commits like chore, docs, style, refactor, test do not trigger releases"
    )
    click.echo()
    click.echo("Version bump: NO")
    click.echo("=" * 80)


def _write_github_output(path: str | None, version_changed: bool) -> None:
    if not path:
        return
    value = "true" if version_changed else "false"
    with open(path, "a") as f:
        f.write(f"version_changed={value}\n")


@click.group()
def release() -> None:
    pass


@release.command()
@click.option("--dry-run", is_flag=True, help="Run without making any changes")
@click.option("--no-ci", is_flag=True, help="Run outside of CI environment")
@click.option(
    "--branches", multiple=True, default=["main"], help="Branches to release from"
)
@click.option(
    "--tag-format", default="v${version}", help="Git tag format template"
)
@click.option(
    "--changelog-file", default="CHANGELOG.md", help="Path to changelog file"
)
@click.option("--draft-release", is_flag=True, help="Create draft GitHub release")
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to YAML configuration file",
)
def run(
    dry_run: bool,
    no_ci: bool,
    branches: tuple[str, ...],
    tag_format: str,
    changelog_file: str,
    draft_release: bool,
    config: Path | None,
) -> None:
    release_config = _load_config(config)
    release_config.options.dry_run = dry_run
    release_config.options.ci = not no_ci
    release_config.options.branches = list(branches)
    release_config.options.tag_format = tag_format
    release_config.changelog.changelog_file = changelog_file
    release_config.github.draft_release = draft_release

    orchestrator = SemanticReleaseOrchestrator(
        config=release_config, cwd=Path.cwd()
    )

    try:
        click.echo("=" * 80)
        click.echo("Starting Semantic Release")
        click.echo("=" * 80)
        result = orchestrator.run()
        github_output = os.environ.get("GITHUB_OUTPUT")
        click.echo()
        click.echo("=" * 80)
        if result:
            _print_release_result(result, orchestrator)
            _write_github_output(github_output, True)
        else:
            _print_no_release_result(orchestrator)
            _write_github_output(github_output, False)
    except Exception as e:
        click.echo()
        click.echo("=" * 80, err=True)
        click.echo("Release Failed", err=True)
        click.echo("=" * 80, err=True)
        click.echo(f"  Error: {str(e)}", err=True)
        click.echo("=" * 80, err=True)
        raise click.Abort() from e


@release.command()
@click.option(
    "--input", "-i",
    type=click.Path(exists=True, path_type=Path),
    default="release.config.js",
    help="Path to JavaScript configuration file",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=".releaserc.yaml",
    help="Path to output YAML configuration file",
)
def convert(input: Path, output: Path) -> None:
    try:
        converter = ConfigConverter()
        yaml_config = converter.convert_js_to_yaml(input, output)
        click.echo(f"Successfully converted {input} to {output}")
        click.echo("\nGenerated configuration:")
        click.echo(
            f"  Branches: {yaml_config.get('options', {}).get('branches', [])}"
        )
        click.echo(
            f"  Tag Format: {yaml_config.get('options', {}).get('tag_format', 'v${version}')}"
        )
        if "commit_analyzer" in yaml_config:
            rules = yaml_config["commit_analyzer"].get("release_rules", [])
            click.echo(f"  Release Rules: {len(rules)} rules")
        click.echo("\nYou can now use this configuration with:")
        click.echo(f"  semantic-release run --config {output}")
    except Exception as e:
        click.echo(f"Conversion failed: {str(e)}", err=True)
        raise click.Abort() from e


if __name__ == "__main__":
    release()
