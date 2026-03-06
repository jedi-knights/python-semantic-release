from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from python_semantic_release.models import (
    ChangelogConfig,
    CommitAnalyzerConfig,
    GitConfig,
    GitHubConfig,
    Options,
    ReleaseNotesConfig,
    ReleaseRule,
    VersionConfig,
)
from python_semantic_release.orchestrator import SemanticReleaseConfig


class ConfigLoader:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False

    def load(self) -> SemanticReleaseConfig:
        with open(self.config_path) as f:
            data = self.yaml.load(f)
        config = SemanticReleaseConfig()
        self._apply_sections(config, data)
        return config

    def _apply_sections(
        self, config: SemanticReleaseConfig, data: dict[str, Any]
    ) -> None:
        section_map = {
            "options": (self._load_options, "options"),
            "commit_analyzer": (self._load_commit_analyzer, "commit_analyzer"),
            "release_notes": (self._load_release_notes, "release_notes"),
            "changelog": (self._load_changelog, "changelog"),
            "github": (self._load_github, "github"),
            "git": (self._load_git, "git"),
            "version": (self._load_version, "version"),
        }
        for key, (loader, attr) in section_map.items():
            if key in data:
                setattr(config, attr, loader(data[key]))

    def _load_options(self, data: dict[str, Any]) -> Options:
        return Options(
            tag_format=data.get("tag_format", "v${version}"),
            branches=data.get("branches", ["main"]),
            repository_url=data.get("repository_url", ""),
            dry_run=data.get("dry_run", False),
            ci=data.get("ci", True),
        )

    def _load_commit_analyzer(
        self, data: dict[str, Any]
    ) -> CommitAnalyzerConfig:
        release_rules = [
            ReleaseRule(
                type=rule.get("type"),
                scope=rule.get("scope"),
                breaking=rule.get("breaking"),
                revert=rule.get("revert"),
                release=rule.get("release"),
            )
            for rule in data.get("release_rules", [])
        ]
        return CommitAnalyzerConfig(
            preset=data.get("preset", "angular"),
            release_rules=release_rules,
            parser_opts=data.get("parser_opts", {}),
        )

    def _load_release_notes(self, data: dict[str, Any]) -> ReleaseNotesConfig:
        return ReleaseNotesConfig(
            preset=data.get("preset", "angular"),
            writer_opts=data.get("writer_opts", {}),
            parser_opts=data.get("parser_opts", {}),
            host=data.get("host", "https://github.com"),
            link_compare=data.get("link_compare", True),
            link_references=data.get("link_references", True),
        )

    def _load_changelog(self, data: dict[str, Any]) -> ChangelogConfig:
        return ChangelogConfig(
            changelog_file=data.get("changelog_file", "CHANGELOG.md"),
            changelog_title=data.get("changelog_title", "# Changelog"),
        )

    def _load_github(self, data: dict[str, Any]) -> GitHubConfig:
        return GitHubConfig(
            assets=data.get("assets", []),
            success_comment=data.get("success_comment"),
            fail_comment=data.get("fail_comment"),
            labels=data.get("labels", []),
            assignees=data.get("assignees", []),
            draft_release=data.get("draft_release", False),
        )

    def _load_git(self, data: dict[str, Any]) -> GitConfig:
        return GitConfig(
            assets=data.get(
                "assets", ["CHANGELOG.md", "pyproject.toml", "VERSION"]
            ),
            message=data.get(
                "message",
                "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}",
            ),
        )

    def _load_version(self, data: dict[str, Any]) -> VersionConfig:
        return VersionConfig(
            version_files=data.get(
                "version_files", ["VERSION", "pyproject.toml:project.version"]
            )
        )
