from unittest.mock import MagicMock

from python_semantic_release.git.plugin import GitPlugin
from python_semantic_release.models import GitConfig, Release
from tests.conftest import make_context


def _mock_git_service(modified_files=None):
    svc = MagicMock()
    svc.get_modified_files.return_value = modified_files or []
    return svc


def _ctx_with_release(tmp_path, version="1.1.0"):
    ctx = make_context(tmp_path)
    ctx.next_release = Release(
        version=version, git_tag=f"v{version}", git_head="sha"
    )
    return ctx


def test_prepare_no_next_release_is_noop(tmp_path):
    svc = _mock_git_service()
    plugin = GitPlugin(git_service=svc)
    ctx = make_context(tmp_path)
    ctx.next_release = None
    plugin.prepare(ctx)
    svc.get_modified_files.assert_not_called()


def test_prepare_commits_matched_files(tmp_path):
    svc = _mock_git_service(modified_files=["CHANGELOG.md", "VERSION"])
    plugin = GitPlugin(
        config=GitConfig(assets=["CHANGELOG.md", "VERSION"]),
        git_service=svc,
    )
    ctx = _ctx_with_release(tmp_path)
    plugin.prepare(ctx)
    svc.add_files.assert_called_once_with(["CHANGELOG.md", "VERSION"])
    svc.commit.assert_called_once()


def test_prepare_skips_unmatched_files(tmp_path):
    svc = _mock_git_service(modified_files=["src/main.py"])
    plugin = GitPlugin(
        config=GitConfig(assets=["CHANGELOG.md"]),
        git_service=svc,
    )
    ctx = _ctx_with_release(tmp_path)
    plugin.prepare(ctx)
    svc.add_files.assert_not_called()
    svc.commit.assert_not_called()


def test_prepare_no_modified_files_skips_commit(tmp_path):
    svc = _mock_git_service(modified_files=[])
    plugin = GitPlugin(git_service=svc)
    ctx = _ctx_with_release(tmp_path)
    plugin.prepare(ctx)
    svc.commit.assert_not_called()


def test_prepare_commit_message_contains_version(tmp_path):
    svc = _mock_git_service(modified_files=["CHANGELOG.md"])
    plugin = GitPlugin(
        config=GitConfig(assets=["CHANGELOG.md"]),
        git_service=svc,
    )
    ctx = _ctx_with_release(tmp_path, version="2.0.0")
    plugin.prepare(ctx)
    commit_msg = svc.commit.call_args[0][0]
    assert "2.0.0" in commit_msg


def test_prepare_glob_pattern_matching(tmp_path):
    svc = _mock_git_service(modified_files=["dist/package.tar.gz"])
    plugin = GitPlugin(
        config=GitConfig(assets=["dist/*.tar.gz"]),
        git_service=svc,
    )
    ctx = _ctx_with_release(tmp_path)
    plugin.prepare(ctx)
    svc.add_files.assert_called_once()


def test_prepare_creates_git_service_when_none(tmp_path, monkeypatch):
    created_service = _mock_git_service(modified_files=[])
    monkeypatch.setattr(
        "python_semantic_release.git.plugin.GitService",
        lambda **kwargs: created_service,
    )
    plugin = GitPlugin(git_service=None)
    ctx = _ctx_with_release(tmp_path)
    plugin.prepare(ctx)
    created_service.get_modified_files.assert_called_once()


def test_render_message_replaces_version(tmp_path):
    plugin = GitPlugin(
        config=GitConfig(
            message="release: ${nextRelease.version}",
            assets=[],
        )
    )
    ctx = _ctx_with_release(tmp_path, version="3.0.0")
    msg = plugin._render_message(ctx)
    assert msg == "release: 3.0.0"


def test_render_message_replaces_tag(tmp_path):
    plugin = GitPlugin(
        config=GitConfig(
            message="tag: ${nextRelease.gitTag}",
            assets=[],
        )
    )
    ctx = _ctx_with_release(tmp_path, version="3.0.0")
    msg = plugin._render_message(ctx)
    assert msg == "tag: v3.0.0"


def test_render_message_no_next_release_returns_empty(tmp_path):
    plugin = GitPlugin()
    ctx = make_context(tmp_path)
    ctx.next_release = None
    assert plugin._render_message(ctx) == ""
