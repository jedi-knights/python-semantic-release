from pathlib import Path

import pytest

from python_semantic_release.config_converter import ConfigConverter


@pytest.fixture
def converter() -> ConfigConverter:
    return ConfigConverter()


def _write_js(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "release.config.js"
    path.write_text(content)
    return path


# --- _has_plugin ---

def test_has_plugin_string_match(converter):
    cfg = {"plugins": ["@semantic-release/commit-analyzer"]}
    assert converter._has_plugin(cfg, "commit-analyzer") is True


def test_has_plugin_string_no_match(converter):
    cfg = {"plugins": ["@semantic-release/github"]}
    assert converter._has_plugin(cfg, "commit-analyzer") is False


def test_has_plugin_list_match(converter):
    cfg = {"plugins": [["@semantic-release/github", {"draft": True}]]}
    assert converter._has_plugin(cfg, "github") is True


def test_has_plugin_empty_plugins(converter):
    assert converter._has_plugin({}, "anything") is False


def test_has_plugin_no_plugins_key(converter):
    assert converter._has_plugin({"branches": ["main"]}, "github") is False


# --- _has_git_plugin ---

def test_has_git_plugin_true(converter):
    cfg = {"plugins": ["@semantic-release/git"]}
    assert converter._has_git_plugin(cfg) is True


def test_has_git_plugin_excludes_github(converter):
    cfg = {"plugins": ["@semantic-release/github"]}
    assert converter._has_git_plugin(cfg) is False


def test_has_git_plugin_list_form(converter):
    cfg = {"plugins": [["@semantic-release/git", {"assets": ["CHANGELOG.md"]}]]}
    assert converter._has_git_plugin(cfg) is True


# --- _normalize_release_value ---

def test_normalize_false_literal(converter):
    assert converter._normalize_release_value(False) is None


def test_normalize_false_string(converter):
    assert converter._normalize_release_value("false") is None


def test_normalize_minor(converter):
    assert converter._normalize_release_value("minor") == "minor"


def test_normalize_major(converter):
    assert converter._normalize_release_value("major") == "major"


# --- _transform_release_rule ---

def test_transform_rule_type_only(converter):
    result = converter._transform_release_rule({"type": "feat", "release": "minor"})
    assert result["type"] == "feat"
    assert result["release"] == "minor"


def test_transform_rule_false_release(converter):
    result = converter._transform_release_rule({"type": "docs", "release": False})
    assert result["release"] is None


def test_transform_rule_with_scope(converter):
    result = converter._transform_release_rule(
        {"type": "feat", "scope": "api", "release": "minor"}
    )
    assert result["scope"] == "api"


def test_transform_rule_omits_missing_keys(converter):
    result = converter._transform_release_rule({"type": "fix", "release": "patch"})
    assert "scope" not in result
    assert "breaking" not in result


# --- _build_options_section ---

def test_build_options_with_branches(converter):
    result = converter._build_options_section({"branches": ["main"]})
    assert result is not None
    assert result["branches"] == ["main"]


def test_build_options_with_tag_format(converter):
    result = converter._build_options_section({"tagFormat": "v${version}"})
    assert result["tag_format"] == "v${version}"


def test_build_options_none_when_no_relevant_keys(converter):
    result = converter._build_options_section({"preset": "angular"})
    assert result is None


def test_build_options_includes_repository_url(converter):
    result = converter._build_options_section(
        {"branches": ["main"], "repositoryUrl": "https://github.com/x/y"}
    )
    assert result["repository_url"] == "https://github.com/x/y"


# --- _transform_config ---

def test_transform_config_always_includes_version(converter):
    result = converter._transform_config({})
    assert "version" in result
    assert "VERSION" in result["version"]["version_files"]


def test_transform_config_options_section(converter):
    result = converter._transform_config({"branches": ["main"]})
    assert "options" in result
    assert result["options"]["branches"] == ["main"]


def test_transform_config_no_options_when_not_needed(converter):
    result = converter._transform_config({"preset": "angular"})
    assert "options" not in result


def test_transform_config_commit_analyzer_with_preset(converter):
    result = converter._transform_config({"preset": "angular"})
    assert "commit_analyzer" in result
    assert result["commit_analyzer"]["preset"] == "angular"


def test_transform_config_release_notes_plugin(converter):
    result = converter._transform_config(
        {"plugins": ["@semantic-release/release-notes-generator"]}
    )
    assert "release_notes" in result


def test_transform_config_changelog_plugin(converter):
    result = converter._transform_config(
        {"plugins": ["@semantic-release/changelog"]}
    )
    assert "changelog" in result


def test_transform_config_changelog_file_from_js(converter):
    result = converter._transform_config(
        {
            "plugins": ["@semantic-release/changelog"],
            "changelogFile": "CHANGES.md",
        }
    )
    assert result["changelog"]["changelog_file"] == "CHANGES.md"


def test_transform_config_changelog_default_file(converter):
    result = converter._transform_config(
        {"plugins": ["@semantic-release/changelog"]}
    )
    assert result["changelog"]["changelog_file"] == "CHANGELOG.md"


def test_transform_config_github_plugin(converter):
    result = converter._transform_config(
        {"plugins": [["@semantic-release/github", {"draft": True}]]}
    )
    assert "github" in result


def test_transform_config_git_plugin(converter):
    result = converter._transform_config(
        {
            "plugins": [
                ["@semantic-release/git", {"assets": ["CHANGELOG.md"]}]
            ]
        }
    )
    assert "git" in result
    assert result["git"]["assets"] == ["CHANGELOG.md"]


def test_transform_config_release_rules(converter):
    result = converter._transform_config(
        {
            "releaseRules": [
                {"type": "docs", "release": False},
                {"type": "feat", "release": "minor"},
            ]
        }
    )
    rules = result["commit_analyzer"]["release_rules"]
    assert len(rules) == 2
    assert rules[0]["release"] is None
    assert rules[1]["release"] == "minor"


# --- _extract_github_config ---

def test_extract_github_assets(converter):
    js_config = {
        "plugins": [
            [
                "@semantic-release/github",
                {"assets": [{"path": "dist/**", "label": "dist"}]},
            ]
        ]
    }
    result = converter._extract_github_config(js_config)
    assert "assets" in result


def test_extract_github_success_comment(converter):
    js_config = {
        "plugins": [
            [
                "@semantic-release/github",
                {"successComment": "Released as ${nextRelease.version}"},
            ]
        ]
    }
    result = converter._extract_github_config(js_config)
    assert "success_comment" in result


def test_extract_github_labels(converter):
    js_config = {
        "plugins": [
            ["@semantic-release/github", {"labels": ["released"]}]
        ]
    }
    result = converter._extract_github_config(js_config)
    assert result["labels"] == ["released"]


# --- _extract_git_config ---

def test_extract_git_assets(converter):
    js_config = {
        "plugins": [
            ["@semantic-release/git", {"assets": ["CHANGELOG.md", "VERSION"]}]
        ]
    }
    result = converter._extract_git_config(js_config)
    assert result["assets"] == ["CHANGELOG.md", "VERSION"]


def test_extract_git_commit_message_from_top_level(converter):
    result = converter._extract_git_config(
        {"commitMessage": "chore: release ${nextRelease.version}"}
    )
    assert "release" in result["message"]


def test_extract_git_message_from_plugin(converter):
    js_config = {
        "plugins": [
            ["@semantic-release/git", {"message": "chore: ${nextRelease.version}"}]
        ]
    }
    result = converter._extract_git_config(js_config)
    assert "${nextRelease.version}" in result["message"]
