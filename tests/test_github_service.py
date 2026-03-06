from unittest.mock import MagicMock, patch

import pytest

from python_semantic_release.github.service import GitHubPlugin, GitHubService
from python_semantic_release.models import (
    GitHubConfig,
    Release,
)
from tests.conftest import make_commit, make_context


@pytest.fixture
def service() -> GitHubService:
    return GitHubService(token="test-token")


# --- _extract_repo_info ---

def test_extract_repo_info_https(service):
    owner, repo = service._extract_repo_info(
        "https://github.com/owner/repo.git"
    )
    assert owner == "owner"
    assert repo == "repo"


def test_extract_repo_info_ssh(service):
    owner, repo = service._extract_repo_info("git@github.com:owner/repo.git")
    assert owner == "owner"
    assert repo == "repo"


def test_extract_repo_info_https_no_git_suffix(service):
    owner, repo = service._extract_repo_info(
        "https://github.com/myorg/myrepo"
    )
    assert owner == "myorg"
    assert repo == "myrepo"


def test_extract_repo_info_invalid_raises(service):
    with pytest.raises(ValueError):
        service._extract_repo_info("not-a-url")


# --- get_issues_from_commits ---

def test_get_issues_from_commits_single(service):
    issues = service.get_issues_from_commits(["Closes #42"])
    assert issues == [42]


def test_get_issues_from_commits_multiple(service):
    issues = service.get_issues_from_commits(["Closes #1", "Fixes #2", "Resolves #3"])
    assert issues == [1, 2, 3]


def test_get_issues_from_commits_deduplicates(service):
    issues = service.get_issues_from_commits(["#5", "#5"])
    assert issues == [5]


def test_get_issues_from_commits_none_found(service):
    issues = service.get_issues_from_commits(["just a regular message"])
    assert issues == []


def test_get_issues_from_commits_sorted(service):
    issues = service.get_issues_from_commits(["#10", "#2", "#5"])
    assert issues == [2, 5, 10]


# --- session headers ---

def test_session_has_auth_header(service):
    assert "Authorization" in service.session.headers
    assert "test-token" in service.session.headers["Authorization"]


def test_session_has_accept_header(service):
    assert "Accept" in service.session.headers


# --- create_release (mocked) ---

def test_create_release_calls_correct_endpoint(service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": 1, "upload_url": "https://uploads/assets{?name}", "html_url": "https://github.com/owner/repo/releases/1"
    }
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    result = service.create_release(
        "https://github.com/owner/repo",
        tag="v1.0.0",
        name="1.0.0",
        body="notes",
    )
    assert result["id"] == 1
    call_url = service.session.post.call_args[0][0]
    assert "owner/repo/releases" in call_url


def test_create_release_with_target_commitish(service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 2, "upload_url": "x", "html_url": "y"}
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    service.create_release(
        "https://github.com/owner/repo",
        tag="v1.0.0",
        name="1.0.0",
        body="notes",
        target_commitish="abc123",
    )
    payload = service.session.post.call_args[1]["json"]
    assert payload["target_commitish"] == "abc123"


# --- update_release (mocked) ---

def test_update_release_patches_draft(service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 1, "html_url": "url"}
    mock_resp.raise_for_status = MagicMock()
    service.session.patch = MagicMock(return_value=mock_resp)

    service.update_release("https://github.com/owner/repo", 1, draft=False)
    payload = service.session.patch.call_args[1]["json"]
    assert payload["draft"] is False


# --- comment_on_issue (mocked) ---

def test_comment_on_issue_posts_to_correct_url(service):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    service.comment_on_issue("https://github.com/owner/repo", 5, "Great!")
    call_url = service.session.post.call_args[0][0]
    assert "issues/5/comments" in call_url


# --- add_labels_to_issue (mocked) ---

def test_add_labels_skips_empty_list(service):
    service.session.post = MagicMock()
    service.add_labels_to_issue("https://github.com/owner/repo", 1, [])
    service.session.post.assert_not_called()


def test_add_labels_posts_labels(service):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    service.add_labels_to_issue(
        "https://github.com/owner/repo", 3, ["released"]
    )
    payload = service.session.post.call_args[1]["json"]
    assert "released" in payload["labels"]


# --- upload_release_asset ---

def test_upload_release_asset_posts_to_upload_url(service, tmp_path):
    asset = tmp_path / "dist.tar.gz"
    asset.write_bytes(b"data")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 99}
    mock_resp.raise_for_status = MagicMock()

    with patch("python_semantic_release.github.service.requests.post", return_value=mock_resp):
        result = service.upload_release_asset(
            "https://uploads.github.com/assets{?name}",
            asset,
            label="Distribution",
        )
    assert result["id"] == 99


def test_upload_release_asset_strips_template_from_url(service, tmp_path):
    asset = tmp_path / "file.zip"
    asset.write_bytes(b"zip")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    mock_resp.raise_for_status = MagicMock()

    with patch("python_semantic_release.github.service.requests.post", return_value=mock_resp) as mock_post:
        service.upload_release_asset("https://uploads/assets{?name,label}", asset, "lbl")
    call_url = mock_post.call_args[0][0]
    assert "{" not in call_url


# --- GitHubPlugin.__init__ ---

def test_github_plugin_reads_token_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    plugin = GitHubPlugin()
    assert plugin.service.token == "env-token"


def test_github_plugin_raises_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        GitHubPlugin()


def test_github_plugin_accepts_explicit_token():
    plugin = GitHubPlugin(token="explicit-token")
    assert plugin.service.token == "explicit-token"


# --- verify_conditions ---

def test_verify_conditions_passes_with_token():
    plugin = GitHubPlugin(token="tok")
    plugin.verify_conditions(MagicMock())  # should not raise


# --- publish ---

def test_publish_creates_release(tmp_path):
    plugin = GitHubPlugin(token="tok")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": 1,
        "upload_url": "https://uploads/assets{?name}",
        "html_url": "https://github.com/owner/repo/releases/1",
    }
    mock_resp.raise_for_status = MagicMock()
    plugin.service.session.post = MagicMock(return_value=mock_resp)

    patch_resp = MagicMock()
    patch_resp.json.return_value = {"html_url": "https://github.com/owner/repo/releases/1"}
    patch_resp.raise_for_status = MagicMock()
    plugin.service.session.patch = MagicMock(return_value=patch_resp)

    ctx = make_context(tmp_path)
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    result = plugin.publish(ctx)
    assert result.version == "1.1.0"


def test_publish_raises_without_next_release(tmp_path):
    plugin = GitHubPlugin(token="tok")
    ctx = make_context(tmp_path)
    ctx.next_release = None
    with pytest.raises(ValueError):
        plugin.publish(ctx)


def test_publish_draft_release_skips_update(tmp_path):
    plugin = GitHubPlugin(config=GitHubConfig(draft_release=True), token="tok")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": 5,
        "upload_url": "https://uploads/assets{?name}",
        "html_url": "https://url",
    }
    mock_resp.raise_for_status = MagicMock()
    plugin.service.session.post = MagicMock(return_value=mock_resp)
    plugin.service.session.patch = MagicMock()

    ctx = make_context(tmp_path)
    ctx.next_release = Release(version="2.0.0", git_tag="v2.0.0", git_head="sha")
    plugin.publish(ctx)
    plugin.service.session.patch.assert_not_called()


# --- success ---

def test_success_noop_without_success_comment(tmp_path):
    plugin = GitHubPlugin(config=GitHubConfig(success_comment=None), token="tok")
    plugin.service.session.post = MagicMock()
    ctx = make_context(tmp_path, commits=[make_commit(message="feat: x")])
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    plugin.success(ctx)
    plugin.service.session.post.assert_not_called()


def test_success_noop_without_next_release(tmp_path):
    plugin = GitHubPlugin(config=GitHubConfig(success_comment="Released!"), token="tok")
    plugin.service.session.post = MagicMock()
    ctx = make_context(tmp_path)
    ctx.next_release = None
    plugin.success(ctx)
    plugin.service.session.post.assert_not_called()


def test_success_comments_on_issues(tmp_path):
    plugin = GitHubPlugin(
        config=GitHubConfig(success_comment="Released as ${nextRelease.version}"),
        token="tok",
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    plugin.service.session.post = MagicMock(return_value=mock_resp)

    ctx = make_context(
        tmp_path,
        commits=[make_commit(message="fix: thing Closes #10")],
    )
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    plugin.success(ctx)
    plugin.service.session.post.assert_called()
    call_url = plugin.service.session.post.call_args[0][0]
    assert "issues/10/comments" in call_url


# --- fail ---

def test_fail_noop_without_fail_comment(tmp_path):
    plugin = GitHubPlugin(config=GitHubConfig(fail_comment=None), token="tok")
    plugin.service.session.post = MagicMock()
    ctx = make_context(tmp_path)
    plugin.fail(ctx, RuntimeError("boom"))
    plugin.service.session.post.assert_not_called()


# --- _render_template ---

def test_render_template_replaces_version(tmp_path):
    plugin = GitHubPlugin(token="tok")
    ctx = make_context(tmp_path)
    ctx.next_release = Release(version="2.0.0", git_tag="v2.0.0", git_head="sha")
    result = plugin._render_template("Released as ${nextRelease.version}", ctx)
    assert result == "Released as 2.0.0"


def test_render_template_replaces_git_tag(tmp_path):
    plugin = GitHubPlugin(token="tok")
    ctx = make_context(tmp_path)
    ctx.next_release = Release(version="2.0.0", git_tag="v2.0.0", git_head="sha")
    result = plugin._render_template("Tag: ${nextRelease.gitTag}", ctx)
    assert result == "Tag: v2.0.0"


def test_render_template_no_next_release(tmp_path):
    plugin = GitHubPlugin(token="tok")
    ctx = make_context(tmp_path)
    ctx.next_release = None
    result = plugin._render_template("${nextRelease.version}", ctx)
    assert result == "${nextRelease.version}"


# --- verify_conditions: empty token ---

def test_verify_conditions_raises_when_token_empty(tmp_path):
    plugin = GitHubPlugin(token="tok")
    plugin.service.token = ""
    with pytest.raises(ValueError, match="GitHub token is required"):
        plugin.verify_conditions(MagicMock())


# --- upload_release_asset: unknown MIME type ---

def test_upload_release_asset_unknown_mime_type(service, tmp_path):
    asset = tmp_path / "file.xyz_unknown"
    asset.write_bytes(b"data")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 1}
    mock_resp.raise_for_status = MagicMock()

    with patch("python_semantic_release.github.service.requests.post", return_value=mock_resp) as mock_post:
        service.upload_release_asset("https://uploads/assets{?name}", asset, "label")

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Content-Type"] == "application/octet-stream"


# --- _upload_assets ---

def test_upload_assets_uploads_matching_files(tmp_path):
    (tmp_path / "dist").mkdir()
    dist = tmp_path / "dist" / "package.tar.gz"
    dist.write_bytes(b"archive")

    plugin = GitHubPlugin(
        config=GitHubConfig(assets=[{"path": "dist/*.tar.gz", "label": "dist"}]),
        token="tok",
    )
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 1}
    mock_resp.raise_for_status = MagicMock()

    with patch("python_semantic_release.github.service.requests.post", return_value=mock_resp):
        ctx = make_context(tmp_path)
        plugin._upload_assets(ctx, "https://uploads/assets{?name}")

    # upload was triggered since the file matches
    assert mock_resp.json.called


# --- success with labels ---

def test_success_adds_labels_to_issues(tmp_path):
    plugin = GitHubPlugin(
        config=GitHubConfig(
            success_comment="Released!",
            labels=["released"],
        ),
        token="tok",
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    plugin.service.session.post = MagicMock(return_value=mock_resp)

    ctx = make_context(
        tmp_path,
        commits=[make_commit(message="fix: thing Closes #7")],
    )
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    plugin.success(ctx)

    calls = [str(call) for call in plugin.service.session.post.call_args_list]
    assert any("labels" in c for c in calls)


def test_success_swallows_comment_exception(tmp_path):
    plugin = GitHubPlugin(
        config=GitHubConfig(success_comment="Released!"),
        token="tok",
    )
    plugin.service.session.post = MagicMock(side_effect=RuntimeError("api down"))

    ctx = make_context(
        tmp_path,
        commits=[make_commit(message="fix: patch #99")],
    )
    ctx.next_release = Release(version="1.1.0", git_tag="v1.1.0", git_head="sha")
    plugin.success(ctx)  # should not raise despite the error
