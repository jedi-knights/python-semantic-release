from ruamel.yaml import YAML

from python_semantic_release.config.loader import ConfigLoader


def _write_yaml(path, data):
    yaml = YAML()
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


def test_load_empty_file_returns_defaults(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(cfg_path, {})
    config = ConfigLoader(cfg_path).load()
    assert config.options.tag_format == "v${version}"
    assert config.options.branches == ["main"]


def test_load_options_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "options": {
                "tag_format": "v${version}-rc",
                "branches": ["main", "develop"],
                "dry_run": True,
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.options.tag_format == "v${version}-rc"
    assert config.options.branches == ["main", "develop"]
    assert config.options.dry_run is True


def test_load_commit_analyzer_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "commit_analyzer": {
                "preset": "angular",
                "release_rules": [
                    {"type": "docs", "release": "patch"},
                    {"type": "style", "release": None},
                ],
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.commit_analyzer.preset == "angular"
    assert len(config.commit_analyzer.release_rules) == 2
    assert config.commit_analyzer.release_rules[0].type == "docs"
    assert config.commit_analyzer.release_rules[0].release == "patch"
    assert config.commit_analyzer.release_rules[1].release is None


def test_load_release_notes_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "release_notes": {
                "preset": "angular",
                "link_compare": False,
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.release_notes.link_compare is False


def test_load_changelog_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "changelog": {
                "changelog_file": "CHANGES.md",
                "changelog_title": "# Changes",
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.changelog.changelog_file == "CHANGES.md"
    assert config.changelog.changelog_title == "# Changes"


def test_load_github_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "github": {
                "draft_release": True,
                "labels": ["released"],
                "success_comment": "Released as ${nextRelease.version}",
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.github.draft_release is True
    assert "released" in config.github.labels
    assert config.github.success_comment is not None


def test_load_git_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "git": {
                "assets": ["CHANGELOG.md"],
                "message": "chore: release ${nextRelease.version}",
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.git.assets == ["CHANGELOG.md"]
    assert "release" in config.git.message


def test_load_version_section(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "version": {
                "version_files": ["VERSION", "setup.cfg:metadata.version"],
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert "VERSION" in config.version.version_files
    assert "setup.cfg:metadata.version" in config.version.version_files


def test_load_all_sections_together(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "options": {"branches": ["main"]},
            "commit_analyzer": {"preset": "angular"},
            "release_notes": {"preset": "angular"},
            "changelog": {"changelog_file": "CHANGELOG.md"},
            "github": {"draft_release": False},
            "git": {"assets": ["CHANGELOG.md"]},
            "version": {"version_files": ["VERSION"]},
        },
    )
    config = ConfigLoader(cfg_path).load()
    assert config.options.branches == ["main"]
    assert config.commit_analyzer.preset == "angular"
    assert config.changelog.changelog_file == "CHANGELOG.md"
    assert config.version.version_files == ["VERSION"]


def test_load_commit_analyzer_rule_with_scope(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {
            "commit_analyzer": {
                "release_rules": [
                    {"type": "feat", "scope": "api", "release": "minor"},
                ]
            }
        },
    )
    config = ConfigLoader(cfg_path).load()
    rule = config.commit_analyzer.release_rules[0]
    assert rule.scope == "api"


def test_load_options_ci_default_true(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(cfg_path, {"options": {}})
    config = ConfigLoader(cfg_path).load()
    assert config.options.ci is True


def test_load_options_repository_url(tmp_path):
    cfg_path = tmp_path / ".releaserc.yaml"
    _write_yaml(
        cfg_path,
        {"options": {"repository_url": "https://github.com/owner/repo"}},
    )
    config = ConfigLoader(cfg_path).load()
    assert config.options.repository_url == "https://github.com/owner/repo"
