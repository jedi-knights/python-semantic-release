from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ReleaseType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass(frozen=True)
class Commit:
    hash: str
    message: str
    author_name: str
    author_email: str
    date: datetime
    body: str = ""


@dataclass
class ParsedCommit:
    type: str | None
    scope: str | None
    subject: str
    body: str
    breaking: bool
    mentions: list[str]
    references: list[dict[str, Any]]
    revert: bool
    raw_commit: Commit


@dataclass
class Branch:
    name: str
    type: str = "release"
    channel: str | None = None
    prerelease: str | None = None


@dataclass
class Release:
    version: str
    git_tag: str
    git_head: str
    notes: str = ""
    channel: str | None = None
    url: str = ""
    type: ReleaseType | None = None


@dataclass
class Options:
    tag_format: str = "v${version}"
    branches: list[str] = field(default_factory=lambda: ["main"])
    repository_url: str = ""
    dry_run: bool = False
    ci: bool = True


@dataclass
class Context:
    cwd: Path
    env: dict[str, str]
    branch: Branch
    commits: list[Commit]
    options: Options
    last_release: Release | None = None
    next_release: Release | None = None
    releases: list[Release] = field(default_factory=list)


@dataclass
class ReleaseRule:
    type: str | None = None
    scope: str | None = None
    breaking: bool | None = None
    revert: bool | None = None
    release: str | None = None


@dataclass
class CommitAnalyzerConfig:
    preset: str = "angular"
    release_rules: list[ReleaseRule] = field(default_factory=list)
    parser_opts: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReleaseNotesConfig:
    preset: str = "angular"
    writer_opts: dict[str, Any] = field(default_factory=dict)
    parser_opts: dict[str, Any] = field(default_factory=dict)
    host: str = "https://github.com"
    link_compare: bool = True
    link_references: bool = True


@dataclass
class ChangelogConfig:
    changelog_file: str = "CHANGELOG.md"
    changelog_title: str = "# Changelog"


@dataclass
class GitHubConfig:
    assets: list[dict[str, str]] = field(default_factory=list)
    success_comment: str | None = None
    fail_comment: str | None = None
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    draft_release: bool = False


@dataclass
class GitConfig:
    assets: list[str] = field(
        default_factory=lambda: [
            "CHANGELOG.md",
            "pyproject.toml",
            "VERSION",
        ]
    )
    message: str = "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"


@dataclass
class VersionConfig:
    version_files: list[str] = field(
        default_factory=lambda: ["VERSION", "pyproject.toml:project.version"]
    )
