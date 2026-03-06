from datetime import datetime
from pathlib import Path

from python_semantic_release.models import (
    Branch,
    ChangelogConfig,
    Commit,
    CommitAnalyzerConfig,
    Context,
    GitConfig,
    GitHubConfig,
    Options,
    ParsedCommit,
    Release,
    ReleaseNotesConfig,
    ReleaseRule,
    ReleaseType,
    VersionConfig,
)


def test_release_type_values():
    assert ReleaseType.MAJOR.value == "major"
    assert ReleaseType.MINOR.value == "minor"
    assert ReleaseType.PATCH.value == "patch"


def test_commit_is_frozen():
    commit = Commit(
        hash="abc",
        message="feat: x",
        author_name="A",
        author_email="a@b.com",
        date=datetime.now(),
    )
    try:
        commit.hash = "xyz"  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except Exception:
        pass


def test_commit_defaults_empty_body():
    commit = Commit(
        hash="h",
        message="m",
        author_name="n",
        author_email="e",
        date=datetime.now(),
    )
    assert commit.body == ""


def test_parsed_commit_fields():
    raw = Commit(
        hash="h",
        message="feat: x",
        author_name="n",
        author_email="e",
        date=datetime.now(),
    )
    pc = ParsedCommit(
        type="feat",
        scope="api",
        subject="add x",
        body="",
        breaking=False,
        mentions=["user"],
        references=[{"issue": "1"}],
        revert=False,
        raw_commit=raw,
    )
    assert pc.type == "feat"
    assert pc.scope == "api"
    assert pc.breaking is False
    assert pc.raw_commit is raw


def test_branch_defaults():
    b = Branch(name="main")
    assert b.type == "release"
    assert b.channel is None
    assert b.prerelease is None


def test_release_defaults():
    r = Release(version="1.0.0", git_tag="v1.0.0", git_head="sha")
    assert r.notes == ""
    assert r.url == ""
    assert r.type is None
    assert r.channel is None


def test_options_defaults():
    o = Options()
    assert o.tag_format == "v${version}"
    assert o.branches == ["main"]
    assert o.dry_run is False
    assert o.ci is True


def test_context_defaults():
    ctx = Context(
        cwd=Path("/tmp"),
        env={},
        branch=Branch(name="main"),
        commits=[],
        options=Options(),
    )
    assert ctx.last_release is None
    assert ctx.next_release is None
    assert ctx.releases == []


def test_release_rule_all_none_by_default():
    r = ReleaseRule()
    assert r.type is None
    assert r.scope is None
    assert r.breaking is None
    assert r.revert is None
    assert r.release is None


def test_commit_analyzer_config_defaults():
    c = CommitAnalyzerConfig()
    assert c.preset == "angular"
    assert c.release_rules == []
    assert c.parser_opts == {}


def test_release_notes_config_defaults():
    c = ReleaseNotesConfig()
    assert c.preset == "angular"
    assert c.host == "https://github.com"
    assert c.link_compare is True
    assert c.link_references is True


def test_changelog_config_defaults():
    c = ChangelogConfig()
    assert c.changelog_file == "CHANGELOG.md"
    assert c.changelog_title == "# Changelog"


def test_github_config_defaults():
    c = GitHubConfig()
    assert c.assets == []
    assert c.labels == []
    assert c.draft_release is False
    assert c.success_comment is None


def test_git_config_defaults():
    c = GitConfig()
    assert "CHANGELOG.md" in c.assets
    assert "VERSION" in c.assets
    assert "${nextRelease.version}" in c.message


def test_version_config_defaults():
    c = VersionConfig()
    assert "VERSION" in c.version_files
    assert "pyproject.toml:project.version" in c.version_files
