from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from python_semantic_release.js_config_parser import JSConfigParser


class ConfigConverter:
    def __init__(self) -> None:
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def convert_js_to_yaml(
        self, js_path: Path, yaml_path: Path
    ) -> dict[str, Any]:
        parser = JSConfigParser(js_path)
        js_config = parser.parse()
        yaml_config = self._transform_config(js_config)
        with open(yaml_path, "w") as f:
            self.yaml.dump(yaml_config, f)
        return yaml_config

    # --- plugin detection ---

    def _has_plugin(self, js_config: dict[str, Any], name: str) -> bool:
        for p in js_config.get("plugins", []):
            if isinstance(p, str) and name in p:
                return True
            if isinstance(p, list) and p and name in p[0]:
                return True
        return False

    def _has_commit_analyzer_plugin(self, js_config: dict[str, Any]) -> bool:
        return self._has_plugin(js_config, "commit-analyzer")

    def _has_release_notes_plugin(self, js_config: dict[str, Any]) -> bool:
        return self._has_plugin(js_config, "release-notes-generator")

    def _has_changelog_plugin(self, js_config: dict[str, Any]) -> bool:
        return self._has_plugin(js_config, "changelog")

    def _has_github_plugin(self, js_config: dict[str, Any]) -> bool:
        return self._has_plugin(js_config, "github")

    def _is_git_plugin_name(self, name: str) -> bool:
        return "/git" in name and "github" not in name

    def _has_git_plugin(self, js_config: dict[str, Any]) -> bool:
        for p in js_config.get("plugins", []):
            if isinstance(p, str) and self._is_git_plugin_name(p):
                return True
            if isinstance(p, list) and p and self._is_git_plugin_name(p[0]):
                return True
        return False

    # --- section builders ---

    def _build_options_section(
        self, js_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        if "branches" not in js_config and "tagFormat" not in js_config:
            return None
        opts: dict[str, Any] = {}
        for js_key, yaml_key in [
            ("branches", "branches"),
            ("tagFormat", "tag_format"),
            ("repositoryUrl", "repository_url"),
        ]:
            if js_key in js_config:
                opts[yaml_key] = js_config[js_key]
        return opts

    def _has_commit_analyzer_config(self, js_config: dict[str, Any]) -> bool:
        return (
            "preset" in js_config
            or "releaseRules" in js_config
            or self._has_commit_analyzer_plugin(js_config)
        )

    def _build_commit_analyzer_section(
        self, js_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not self._has_commit_analyzer_config(js_config):
            return None
        analyzer: dict[str, Any] = {}
        if "preset" in js_config:
            analyzer["preset"] = js_config["preset"]
        if "releaseRules" in js_config:
            analyzer["release_rules"] = [
                self._transform_release_rule(r)
                for r in js_config["releaseRules"]
            ]
        return analyzer

    def _build_changelog_section(
        self, js_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not self._has_changelog_plugin(js_config):
            return None
        return {
            "changelog_file": js_config.get("changelogFile", "CHANGELOG.md")
        }

    def _normalize_release_value(self, value: Any) -> Any:
        if value is False or value == "false":
            return None
        return value

    def _transform_release_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        transformed: dict[str, Any] = {}
        for key in ("type", "scope", "breaking", "revert"):
            if key in rule:
                transformed[key] = rule[key]
        if "release" in rule:
            transformed["release"] = self._normalize_release_value(
                rule["release"]
            )
        return transformed

    def _is_named_plugin(self, plugin: list, name: str) -> bool:
        return (
            len(plugin) == 2
            and (plugin[0] == name or plugin[0].endswith(f"/{name}"))
        )

    def _extract_github_config(
        self, js_config: dict[str, Any]
    ) -> dict[str, Any]:
        github_config: dict[str, Any] = {}
        for plugin in js_config.get("plugins", []):
            if isinstance(plugin, list) and self._is_named_plugin(
                plugin, "github"
            ):
                self._apply_github_opts(plugin[1], github_config)
        return github_config

    def _apply_github_opts(
        self, opts: dict[str, Any], out: dict[str, Any]
    ) -> None:
        for js_key, yaml_key in [
            ("assets", "assets"),
            ("successComment", "success_comment"),
            ("failComment", "fail_comment"),
            ("labels", "labels"),
        ]:
            if js_key in opts:
                out[yaml_key] = opts[js_key]

    def _extract_git_config(
        self, js_config: dict[str, Any]
    ) -> dict[str, Any]:
        git_config: dict[str, Any] = {}
        for plugin in js_config.get("plugins", []):
            if isinstance(plugin, list) and self._is_named_plugin(
                plugin, "git"
            ):
                for key in ("assets", "message"):
                    if key in plugin[1]:
                        git_config[key] = plugin[1][key]
        if "commitMessage" in js_config:
            git_config["message"] = js_config["commitMessage"]
        return git_config

    def _transform_config(self, js_config: dict[str, Any]) -> dict[str, Any]:
        yaml_config: dict[str, Any] = {}

        options = self._build_options_section(js_config)
        if options is not None:
            yaml_config["options"] = options

        analyzer = self._build_commit_analyzer_section(js_config)
        if analyzer is not None:
            yaml_config["commit_analyzer"] = analyzer

        if self._has_release_notes_plugin(js_config):
            yaml_config["release_notes"] = {"preset": "angular"}

        changelog = self._build_changelog_section(js_config)
        if changelog is not None:
            yaml_config["changelog"] = changelog

        if self._has_github_plugin(js_config):
            yaml_config["github"] = self._extract_github_config(js_config)

        if self._has_git_plugin(js_config):
            yaml_config["git"] = self._extract_git_config(js_config)

        yaml_config["version"] = {
            "version_files": ["VERSION", "pyproject.toml:project.version"]
        }
        return yaml_config
