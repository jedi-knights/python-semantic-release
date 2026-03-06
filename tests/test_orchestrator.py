from pathlib import Path
from unittest.mock import MagicMock

import pytest

from python_semantic_release.models import (
    Release,
    ReleaseType,
)
from python_semantic_release.orchestrator import (
    SemanticReleaseConfig,
    SemanticReleaseOrchestrator,
)
from tests.conftest import make_commit, make_context


def _make_orchestrator(tmp_path: Path, config=None) -> SemanticReleaseOrchestrator:
    return SemanticReleaseOrchestrator(config=config or SemanticReleaseConfig(), cwd=tmp_path)


def _mock_git_service(
    branch="main",
    last_tag="v1.0.0",
    commits=None,
    repo_url="https://github.com/owner/repo",
    sha="abc123",
):
    svc = MagicMock()
    svc.get_current_branch.return_value = branch
    svc.get_last_tag.return_value = last_tag
    svc.get_commits.return_value = commits if commits is not None else [make_commit()]
    svc.get_repository_url.return_value = repo_url
    svc.get_commit_sha.return_value = sha
    return svc


# --- __init__ ---

def test_init_creates_git_service(tmp_path):
    orch = _make_orchestrator(tmp_path)
    assert orch.git_service is not None


def test_init_creates_commit_analyzer(tmp_path):
    orch = _make_orchestrator(tmp_path)
    assert orch.commit_analyzer is not None


def test_init_creates_version_service(tmp_path):
    orch = _make_orchestrator(tmp_path)
    assert orch.version_service is not None


def test_init_creates_version_updater(tmp_path):
    orch = _make_orchestrator(tmp_path)
    assert orch.version_updater is not None


def test_init_creates_git_plugin(tmp_path):
    orch = _make_orchestrator(tmp_path)
    assert orch.git_plugin is not None


def test_init_no_github_plugin_without_token(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    orch = _make_orchestrator(tmp_path)
    assert orch.github_plugin is None


def test_init_creates_github_plugin_with_token(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    orch = _make_orchestrator(tmp_path)
    assert orch.github_plugin is not None


def test_init_uses_cwd_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    orch = SemanticReleaseOrchestrator()
    assert orch.cwd == tmp_path


# --- _build_context ---

def test_build_context_uses_current_branch(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(branch="develop")
    ctx = orch._build_context()
    assert ctx.branch.name == "develop"


def test_build_context_with_last_tag(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(last_tag="v2.0.0")
    ctx = orch._build_context()
    assert ctx.last_release is not None
    assert ctx.last_release.version == "2.0.0"


def test_build_context_without_last_tag(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(last_tag=None)
    ctx = orch._build_context()
    assert ctx.last_release is None


def test_build_context_sets_repository_url(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(repo_url="https://github.com/x/y")
    orch._build_context()
    assert orch.config.options.repository_url == "https://github.com/x/y"


def test_build_context_includes_commits(tmp_path):
    commits = [make_commit(message="feat: x"), make_commit(message="fix: y")]
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(commits=commits)
    ctx = orch._build_context()
    assert len(ctx.commits) == 2


# --- _verify_conditions ---

def test_verify_conditions_no_github_plugin_is_noop(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = None
    ctx = make_context(tmp_path)
    orch._verify_conditions(ctx)  # should not raise


def test_verify_conditions_calls_github_plugin(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = MagicMock()
    ctx = make_context(tmp_path)
    orch._verify_conditions(ctx)
    orch.github_plugin.verify_conditions.assert_called_once_with(ctx)


# --- _calculate_next_release ---

def test_calculate_next_release_bumps_version(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(sha="newsha")
    ctx = make_context(tmp_path, last_version="1.0.0")
    ctx = orch._calculate_next_release(ctx, ReleaseType.MINOR)
    assert ctx.next_release is not None
    assert ctx.next_release.version == "1.1.0"


def test_calculate_next_release_formats_tag(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(sha="sha")
    ctx = make_context(tmp_path, last_version="1.0.0")
    ctx = orch._calculate_next_release(ctx, ReleaseType.PATCH)
    assert ctx.next_release.git_tag == "v1.0.1"


def test_calculate_next_release_no_last_release(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(sha="sha")
    ctx = make_context(tmp_path)
    ctx.last_release = None
    ctx = orch._calculate_next_release(ctx, ReleaseType.MINOR)
    assert ctx.next_release.version == "0.1.0"


def test_calculate_next_release_sets_git_head(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = _mock_git_service(sha="deadbeef")
    ctx = make_context(tmp_path)
    ctx = orch._calculate_next_release(ctx, ReleaseType.PATCH)
    assert ctx.next_release.git_head == "deadbeef"


# --- _publish_release ---

def test_publish_release_calls_github_plugin(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = MagicMock()
    ctx = make_context(tmp_path)
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    orch.github_plugin.publish.return_value = ctx.next_release
    result = orch._publish_release(ctx)
    orch.github_plugin.publish.assert_called_once_with(ctx)
    assert result is ctx.next_release


def test_publish_release_without_github_returns_next_release(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = None
    ctx = make_context(tmp_path)
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    result = orch._publish_release(ctx)
    assert result is ctx.next_release


def test_publish_release_without_github_no_next_release(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = None
    ctx = make_context(tmp_path)
    ctx.next_release = None
    result = orch._publish_release(ctx)
    assert result is None


# --- _handle_success / _handle_failure ---

def test_handle_success_calls_github_plugin(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = MagicMock()
    ctx = make_context(tmp_path)
    orch._handle_success(ctx)
    orch.github_plugin.success.assert_called_once_with(ctx)


def test_handle_success_no_github_is_noop(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = None
    ctx = make_context(tmp_path)
    orch._handle_success(ctx)  # should not raise


def test_handle_failure_calls_github_plugin(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = MagicMock()
    ctx = make_context(tmp_path)
    err = RuntimeError("boom")
    orch._handle_failure(ctx, err)
    orch.github_plugin.fail.assert_called_once_with(ctx, err)


def test_handle_failure_no_context_is_noop(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = MagicMock()
    orch._handle_failure(None, RuntimeError("boom"))
    orch.github_plugin.fail.assert_not_called()


def test_handle_failure_no_github_is_noop(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.github_plugin = None
    ctx = make_context(tmp_path)
    orch._handle_failure(ctx, RuntimeError("boom"))  # should not raise


# --- run ---

def _patch_orchestrator(orch, release_type=ReleaseType.MINOR, published_release=None):
    orch.git_service = _mock_git_service()
    orch.commit_analyzer = MagicMock()
    orch.commit_analyzer.analyze_commits.return_value = release_type
    orch.notes_generator = MagicMock()
    orch.notes_generator.generate_notes.return_value = "## Notes"
    orch.changelog_service = MagicMock()
    orch.version_updater = MagicMock()
    orch.git_plugin = MagicMock()
    orch.github_plugin = None
    if published_release:
        orch._publish_release = MagicMock(return_value=published_release)


def test_run_returns_none_when_no_release_type(tmp_path):
    orch = _make_orchestrator(tmp_path)
    _patch_orchestrator(orch, release_type=None)
    result = orch.run()
    assert result is None


def test_run_returns_release_when_bumped(tmp_path):
    orch = _make_orchestrator(tmp_path)
    release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    _patch_orchestrator(orch, release_type=ReleaseType.MINOR, published_release=release)
    result = orch.run()
    assert result is not None
    assert result.version == "1.1.0"


def test_run_calls_version_updater(tmp_path):
    orch = _make_orchestrator(tmp_path)
    _patch_orchestrator(orch)
    orch.run()
    orch.version_updater.prepare.assert_called_once()


def test_run_calls_git_plugin_prepare(tmp_path):
    orch = _make_orchestrator(tmp_path)
    _patch_orchestrator(orch)
    orch.run()
    orch.git_plugin.prepare.assert_called_once()


def test_run_calls_changelog_service(tmp_path):
    orch = _make_orchestrator(tmp_path)
    _patch_orchestrator(orch)
    orch.run()
    orch.changelog_service.update_changelog.assert_called_once()


def test_run_reraises_on_exception(tmp_path):
    orch = _make_orchestrator(tmp_path)
    orch.git_service = MagicMock()
    orch.git_service.get_current_branch.side_effect = RuntimeError("git error")
    with pytest.raises(RuntimeError, match="git error"):
        orch.run()
